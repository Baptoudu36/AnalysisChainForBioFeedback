"""Acquisition ECG et diffusion d'un échantillon par datagramme UDP.

Le protocole réseau est volontairement minimal : chaque datagramme contient un
flottant IEEE-754 en double précision, encodé en little-endian (``<d``, 8 octets).
Le programme de réception doit donc connaître la fréquence ``--fs`` et ce format.
"""

import argparse
import socket
import struct
import time

def stream_udp(sample_iterable, dest_ip: str, dest_port: int, fs: float):
    """Envoie les échantillons à cadence fixe et ferme les ressources à l'arrêt.

    Les sources ne temporisent pas elles-mêmes : cette fonction est l'unique
    horloge de la chaîne. Une horloge absolue évite que la durée d'acquisition,
    d'envoi et de ``sleep`` ne s'ajoutent à chaque période.
    """
    if fs <= 0:
        raise ValueError("La fréquence d'échantillonnage doit être strictement positive.")

    period = 1.0 / fs
    report_every = max(1, round(fs * 5))
    sent = 0
    t0 = time.perf_counter()
    next_deadline = t0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # La connexion UDP ne crée pas de session réseau ; elle fixe seulement
        # la destination afin d'utiliser send() et de détecter tôt une erreur.
        sock.connect((dest_ip, dest_port))
        print(f"[Pi] envoi UDP vers {dest_ip}:{dest_port} à {fs} Hz "
              f"(Ctrl+C pour arrêter)")

        for value in sample_iterable:
            packet = struct.pack("<d", float(value))
            sock.send(packet)
            sent += 1

            if sent % report_every == 0:
                elapsed = time.perf_counter() - t0
                print(f"[Pi] {sent} échantillons envoyés ({elapsed:.1f}s écoulées, "
                      f"fs réelle ≈ {sent / elapsed:.1f} Hz)")

            # L'échéance avance d'une période, indépendamment du temps déjà
            # passé dans la lecture ADC ou l'envoi UDP.
            next_deadline += period
            remaining = next_deadline - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
            else:
                # Après un retard, on repart de maintenant : cela évite une
                # rafale d'échantillons qui ne correspondrait plus au signal.
                next_deadline = time.perf_counter()
    except KeyboardInterrupt:
        print("\n[Pi] arrêt demandé par l'utilisateur.")
    finally:
        # Fermer le générateur exécute ses blocs finally (SPI/I2C), même si
        # Ctrl+C survient pendant l'attente dans cette fonction.
        close_source = getattr(sample_iterable, "close", None)
        if callable(close_source):
            close_source()
        sock.close()


def demo_source(fs: float, hr_bpm: float = 72.0):
    """Génère un ECG synthétique à la volée pour tester la chaîne réseau."""
    try:
        import numpy as np
    except ImportError as error:
        raise SystemExit(
            "NumPy est requis uniquement pour le mode demo. Installer avec :\n"
            "  pip install numpy\n"
            f"Erreur d'origine : {error}"
        )

    rng = np.random.default_rng()
    mean_rr = 60.0 / hr_bpm

    def single_beat(t_rel, rr):
        """Modèle simplifié : ondes P, Q, R, S et T par gaussiennes."""
        def g(t, center, amplitude, width):
            return amplitude * np.exp(-((t - center) ** 2) / (2 * width ** 2))

        return (g(t_rel, -0.20 * rr, 0.15, 0.02)
                + g(t_rel, -0.025 * rr, -0.15, 0.006)
                + g(t_rel, 0.0, 1.2, 0.008)
                + g(t_rel, 0.025 * rr, -0.25, 0.008)
                + g(t_rel, 0.30 * rr, 0.30, 0.04))

    while True:
        # Une faible variabilité du rythme rend la démonstration moins parfaite
        # qu'un métronome tout en conservant la fréquence cardiaque moyenne.
        rr = max(0.3, mean_rr + rng.normal(0, 0.03))
        n_samples = max(1, round(rr * fs))

        # Chaque bloc dure un intervalle RR (et non 1,2 RR). Le pic R est à
        # 20 % du bloc : les ondes P, QRS et T restent dans la même fenêtre.
        t_rel = np.arange(n_samples) / fs - 0.20 * rr
        beat = single_beat(t_rel, rr)
        noise = rng.normal(0, 0.02, size=n_samples)
        for value in beat + noise:
            yield float(value)


def acquire_ads1115(fs: float, channel: int = 0):
    """Génère les tensions d'un ADS1115 ; la cadence est gérée par stream_udp."""
    try:
        import board
        import busio
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
    except ImportError as error:
        raise SystemExit(
            "Module ADS1115 manquant sur ce Pi. Installer avec :\n"
            "  pip install adafruit-circuitpython-ads1x15\n"
            f"Erreur d'origine : {error}"
        )

    i2c = busio.I2C(board.SCL, board.SDA)
    try:
        ads = ADS.ADS1115(i2c)
        # On sélectionne le plus petit débit matériel qui couvre la consigne.
        # Sans cela, la valeur par défaut (souvent 128 SPS) limiterait un --fs
        # de 250 Hz et conduirait à relire plusieurs fois la même conversion.
        supported_rates = (8, 16, 32, 64, 128, 250, 475, 860)
        ads.data_rate = next(rate for rate in supported_rates if rate >= fs)
        chan = AnalogIn(ads, getattr(ADS, f"P{channel}"))

        while True:
            yield chan.voltage
    finally:
        i2c.deinit()


def acquire_mcp3008(channel: int = 0):
    """Génère les tensions d'un MCP3008 ; la cadence est gérée par stream_udp."""
    try:
        import spidev
    except ImportError as error:
        raise SystemExit(
            "Module spidev manquant sur ce Pi. Installer avec :\n"
            "  pip install spidev\n"
            f"Erreur d'origine : {error}"
        )

    spi = spidev.SpiDev()
    try:
        spi.open(0, 0)
        spi.max_speed_hz = 1_350_000

        while True:
            # La commande MCP3008 renvoie une valeur ADC non signée sur 10 bits.
            adc = spi.xfer2([1, (8 + channel) << 4, 0])
            value = ((adc[1] & 3) << 8) + adc[2]
            # Vérifier que 3,3 V correspond bien à la tension de référence
            # réellement câblée sur VREF avant toute interprétation physiologique.
            yield value / 1023.0 * 3.3
    finally:
        spi.close()


def main():
    parser = argparse.ArgumentParser(
        description="Serveur d'acquisition ECG (Raspberry Pi -> réseau UDP)."
    )
    parser.add_argument("--mode", choices=["demo", "ads1115", "mcp3008"], default="demo",
                        help="source des échantillons")
    parser.add_argument("--dest-ip", type=str, required=True,
                        help="adresse IP du poste d'analyse (ex. 192.168.1.42)")
    parser.add_argument("--port", type=int, default=5005, help="port UDP destination")
    parser.add_argument("--fs", type=float, default=250.0,
                        help="fréquence d'échantillonnage cible (Hz)")
    parser.add_argument("--fc", type=float, default=72.0, help="FC cible en mode demo (bpm)")
    parser.add_argument("--channel", type=int, default=0, help="canal ADC")
    args = parser.parse_args()

    if args.fs <= 0:
        parser.error("--fs doit être strictement positif.")
    if not 1 <= args.port <= 65_535:
        parser.error("--port doit être compris entre 1 et 65535.")
    if args.mode == "demo" and args.fc <= 0:
        parser.error("--fc doit être strictement positive.")
    if args.mode == "ads1115":
        if not 0 <= args.channel <= 3:
            parser.error("--channel doit être compris entre 0 et 3 pour un ADS1115.")
        if args.fs > 860:
            parser.error("un ADS1115 ne peut pas fournir plus de 860 échantillons/s.")
    elif args.mode == "mcp3008" and not 0 <= args.channel <= 7:
        parser.error("--channel doit être compris entre 0 et 7 pour un MCP3008.")

    if args.mode == "demo":
        source = demo_source(args.fs, hr_bpm=args.fc)
    elif args.mode == "ads1115":
        source = acquire_ads1115(args.fs, channel=args.channel)
    else:
        source = acquire_mcp3008(channel=args.channel)

    stream_udp(source, args.dest_ip, args.port, args.fs)


if __name__ == "__main__":
    main()
