import streamlit as st
import pandas as pd
import json
import schedule
import time
import threading
import requests
import logging
from datetime import datetime
from urllib.parse import urlparse
import jwt
from pathlib import Path
import io
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gurufocus_bot.log'),
        logging.StreamHandler()
    ]
)


class ConfigManager:
    """Gestionnaire de configuration avec persistance sur disque"""

    def __init__(self):
        self.config_file = Path("gurufocus_config.json")
        self.default_config = {
            "telegram": {
                "bot_token": "",
                "chat_id": ""
            },
            "schedule": {
                "execution_times": ["07:25", "19:35"]
            },
            "portfolio": []
        }

    def get_config(self):
        """Récupère la configuration depuis le fichier ou retourne la config par défaut"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Erreur lors de la lecture du fichier de config: {e}")
                return self.default_config.copy()
        else:
            return self.default_config.copy()

    def update_config(self, config):
        """Met à jour la configuration et la sauvegarde sur disque"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la config: {e}")
            return False

    def load_from_file(self, file_content):
        """Charge la configuration depuis un fichier JSON et la sauvegarde"""
        try:
            config_data = json.loads(file_content)
            if self.update_config(config_data):
                return True, "Configuration chargée et sauvegardée avec succès!"
            else:
                return False, "Erreur lors de la sauvegarde de la configuration"
        except Exception as e:
            return False, f"Erreur lors du chargement: {e}"


class GuruFocusAPI:
    """Classe pour interagir avec l'API GuruFocus"""

    def __init__(self):
        self.bearer_token_cookie_key = "password_grant_custom.client"
        self.gurufocus_api_urls = {
            "valuation": "https://www.gurufocus.com/reader/_api/chart/{symbol}/valuation?v=1.7.19",
            "gf_rank": "https://www.gurufocus.com/reader/_api/gf_rank/{mic_symbol}?v=1.7.19",
        }
        self.guru_secret_key = """
MIIEpAIBAAKCAQEAuTF/wURbLidTsbi3uE6hzIlRVxdcjhhdG/1YmWiAaVe5Sin+
QdsjrPabG76BDsgmBPpTlBKLd4S3E3M+j9YnkvO9SxlDldyoCcIfYRY488e4Vpz+
YgqsCevdQA5sSigQR2qVHoZoDYks1Eym3gksSX2YHIq45+OtsJ/ACmnt5/cYpKJN
I+Ja+tpWTY3VBn62KymLV2bLdkw49lx3LljVDujm3m+rbjgM48zyaoZNj9XslWKI
KAPNrIcEFECdDlsnfxV5mNdUGnL8JM7TkAk+COMa1IFMUVDWdkaMHU1Y/t/Jpd4x
C8Vz6Tvj3XWenXCxMxkPmFTXN4+VfILsn+8DMwIDAQABAoIBAQCw964fX1TKW+ZM
dDmLtAhFTgsecEKPvpRrBMO/hO8Au0Viq5I+GEyVIerCrl7hYz2BkDyByN7hTT8t
JPlptbmHYcdHllLRSFSDTq9xtSyjN/zdN5SW15/iszNv3Nh6XKKBvEXXL5ULKkRe
cwkaMCXT7GKJE77ySM1XdLCswuEGwabSMxqG7C3eQRt3oGZhQllGW1suxmb7f9zd
BdJb1jExhuOx2dacR0g+ngg5k8/K23W7nCitJW63vq77XAoD4cloxz5I/rxCeV0O
wH7HRY5HQ3LY9qxVLp6THGtcIrZdCwo73SjVNmrgViH951clT0XVIEy9wzTmWXjy
S1k3mNKxAoGBAN9qsl7C4SCwBB8eYlc8nuX0NmDZSJ/6+8ZapFxposqUEN+x+LJw
XT5wc6uFv+EA5FCWD+4qsBMw5skD3onA/tzTtqmvsV3Hav2CdFMHYZJboU/nUbJE
liJIT/+YHSZauGT+UrnLTYiQPob8hjHuLUvlZdpVNeKcZZIEnpMpjpcXAoGBANQz
uWGSZfzcFlRA3tRaM68NRtP0SdpGUSx/5SNJ54XsU/B5tX0qLLTnChPGE2x1IOkW
jtRTIPFT4QTLc33nMR6iPmqZRwkETXKWS+T0Y/zCGw5+18qYtv4+HzyNoh8irCZz
kTwiFUXt5Pto9D5qrViD75W1YdYx601RmL6IUEZFAoGAEe5yWoCxqPn3mrfJlM7c
wgATzTojRhPS2Vy1DGW+FxxDLnEOUOQL19MWtZGKkPiNWppwtODgOOoX29Jfrha7
XeXwJzZeufQjdi1eQLu67RBFpjAesnwmwKGlKhJ/ZHCrlA+FfDwBARDys8rYynEf
WZQT1K46IPIEhO+x+oW/WAkCgYEAsWNfx+n66csNu3bTD48r/1zI5awkBJydhOaR
JNPGABUUAkWr6qrT3pH4wZjmadbsIQ2jbmjjc/mbdEejDw+x5xrXtILXd/kpyO1N
GmMWJpgYyCBOweSxrI0/zX3UldSFNkuLkEopoGCC94vACWFh8UmxgWO0Grt2KRdZ
6YTIHkUCgYB4vPGRw/B/FSkC2CFvyd1p3kkba6yJbUkM0mD3DvHEYBNZxjJWd/uu
/ezO2PfeST7mHmls1nSwkFMWTtwDYtCxwBsxZ8iVhNmsqYDz78kLSwPPxTeQn97A
hHciL4ObNe50Rhas94NRsOs9HpvUmrfijmBtpF/Kvt93S7kVEnC/Eg==
"""
        self.cookies = self._init_cookies()

    def _init_cookies(self):
        """Initialise les cookies GuruFocus"""
        try:
            response = requests.get(
                "https://www.gurufocus.com/stock/AAPL/summary", verify=False)
            return response.cookies.get_dict()
        except Exception as e:
            logging.error(f"Erreur lors de l'initialisation des cookies: {e}")
            return {}

    def _generate_signature(self, url: str) -> str:
        """Génère la signature JWT pour l'API"""
        now = int(time.time())
        payload = {
            'iat': now,
            'client_time': now,
            'url': self._extract_api_path(url),
            'server_time': now - 2,
            'exp': now + 3600
        }
        return jwt.encode(payload, self.guru_secret_key, algorithm='HS256')

    def _extract_api_path(self, url: str) -> str:
        """Extrait le chemin API de l'URL"""
        parsed = urlparse(url)
        chemin = parsed.path
        index_api = chemin.find('_api')
        return chemin[index_api:] if index_api != -1 else None

    def get_stock_data(self, ticker: str) -> dict:
        """Récupère les données d'une action"""
        try:
            url = self.gurufocus_api_urls['valuation'].format(symbol=ticker)
            signature = self._generate_signature(url)

            headers = {
                'Authorization': f"Bearer {self.cookies.get(self.bearer_token_cookie_key)}",
                'Host': 'www.gurufocus.com',
                'Signature': signature,
                'Content-Type': 'application/json',
                'Referer': url,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'
            }

            response = requests.get(url, headers=headers, verify=False)

            if response.status_code == 200:
                data = response.json()
                price = data.get('price', [])
                last_price = price[-1] if price else []
                current_price = last_price[1] if len(last_price) > 1 else None
                gf_value = data.get('gf_value', None)

                valuation = None
                if gf_value and current_price:
                    valuation = round(
                        ((current_price - gf_value) / gf_value) * 100, 2)

                return {
                    'ticker': ticker,
                    'gf_value': gf_value,
                    'current_price': current_price,
                    'valuation': valuation,
                    'gf_valuation': data.get('gf_valuation', None),
                    'earning_growth_5y': data.get('earning_growth_5y', None),
                    'rvnGrowth5y': data.get('rvnGrowth5y', None),
                    'success': True
                }
            else:
                logging.error(
                    f"Erreur API pour {ticker}: {response.status_code}")
                return {'ticker': ticker, 'success': False, 'error': f"Status: {response.status_code}"}

        except Exception as e:
            logging.error(
                f"Erreur lors de la récupération des données pour {ticker}: {e}")
            return {'ticker': ticker, 'success': False, 'error': str(e)}


class TelegramBot:
    """Classe pour gérer l'envoi de messages Telegram"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_message(self, data: list) -> bool:
        """Envoie un message formaté via Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            message = self._build_message(data)

            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }

            response = requests.post(
                url, data=payload, timeout=10, verify=False)

            if response.status_code == 200:
                logging.info("Message Telegram envoyé avec succès")
                return True
            else:
                logging.error(
                    f"Erreur envoi Telegram: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logging.error(f"Erreur lors de l'envoi du message Telegram: {e}")
            return False

    def _build_message(self, data: list) -> str:
        """Construit le message formaté pour Telegram"""
        message = "<b>📊 Rapport GuruFocus Portfolio</b>\n\n"

        if not data:
            message += "Aucune donnée disponible.\n"
        else:
            message += self._create_telegram_table(data)

        message += f"<i>Dernière mise à jour: {datetime.now().strftime('%H:%M %d/%m/%Y')}</i>"
        return message

    def _create_telegram_table(self, data: list) -> str:
        """Crée un tableau formaté pour Telegram"""
        table = """<pre>
Ticker      | Prix    | GF Val  | %Val   | Pos
------------|---------|---------|--------|----"""

        for item in data:
            if item.get('success', False):
                ticker = item['ticker'][:10]
                prix = f"{item['current_price']:.2f}" if item['current_price'] else "N/A"
                gf_val = f"{item['gf_value']:.2f}" if item['gf_value'] else "N/A"
                valuation = f"{item['valuation']:.1f}%" if item['valuation'] else "N/A"
                position = "✅" if item.get('in_portfolio', False) else "❌"

                line = f"\n{ticker:<11} | {prix:>7} | {gf_val:>7} | {valuation:>6} | {position}"
                table += line

        table += "\n</pre>\n\n"
        return table


class BackgroundScheduler:
    """Gestionnaire de planification en arrière-plan persistant"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.running = False
            self.thread = None
            self.schedule_times = []
            self.callback_func = None
            self.config_manager = None
            self._initialized = True

    def set_config_manager(self, config_manager):
        """Définit le gestionnaire de configuration"""
        self.config_manager = config_manager

    def start_scheduler(self, execution_times: list, callback_func, config_manager):
        """Démarre le planificateur en arrière-plan"""
        if self.running:
            self.stop_scheduler()

        # Nettoyer les anciens jobs
        schedule.clear()

        # Programmer les nouveaux jobs
        for time_str in execution_times:
            schedule.every().day.at(time_str).do(callback_func)

        self.schedule_times = execution_times
        self.callback_func = callback_func
        self.config_manager = config_manager
        self.running = True

        # Démarrer le thread en daemon pour qu'il continue même sans interface
        self.thread = threading.Thread(
            target=self._run_scheduler, daemon=False)
        self.thread.start()

        logging.info(
            f"Planificateur en arrière-plan démarré - Exécution quotidienne à {execution_times}")

    def stop_scheduler(self):
        """Arrête le planificateur"""
        self.running = False
        schedule.clear()
        if self.thread and self.thread.is_alive():
            # Ne pas joindre le thread car il doit continuer à tourner
            pass
        logging.info("Planificateur arrêté")

    def is_running(self):
        """Vérifie si le planificateur est en cours d'exécution"""
        return self.running and self.thread and self.thread.is_alive()

    def _run_scheduler(self):
        """Boucle principale du planificateur qui tourne en permanence"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Vérification toutes les minutes
            except Exception as e:
                logging.error(f"Erreur dans le planificateur: {e}")
                time.sleep(60)


# Instance globale du planificateur
background_scheduler = BackgroundScheduler()


class GuruFocusApp:
    """Application principale"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.guru_api = GuruFocusAPI()
        self.scheduler = background_scheduler
        self.telegram_bot = None

        # Initialiser la configuration depuis le cache persistant
        self.config = self.config_manager.get_config()

        # Initialiser les states pour l'interface seulement
        if 'last_execution' not in st.session_state:
            st.session_state.last_execution = None

        if 'portfolio_data' not in st.session_state:
            st.session_state.portfolio_data = []

        # Configurer le planificateur avec le gestionnaire de config
        self.scheduler.set_config_manager(self.config_manager)

    def run(self):
        """Lance l'application Streamlit"""
        st.set_page_config(
            page_title="GuruFocus Bot",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        st.title("📊 GuruFocus Portfolio Bot")
        st.markdown("---")

        # Sidebar pour la configuration
        with st.sidebar:
            st.header("⚙️ Configuration")
            self._render_config_section()

            st.markdown("---")
            st.header("🕐 Planificateur")
            self._render_scheduler_section()

        # Contenu principal
        col1, col2 = st.columns([2, 1])

        with col1:
            st.header("📋 Portfolio")
            self._render_portfolio_section()

        with col2:
            st.header("📊 Statistiques")
            self._render_stats_section()

        # Section des logs
        st.header("📜 Logs")
        self._render_logs_section()

    def _render_config_section(self):
        """Affiche la section de configuration"""
        st.subheader("📁 Importer Configuration")

        # Vérifier si une configuration existe
        config_exists = (self.config.get('telegram', {}).get('bot_token') or
                         self.config.get('portfolio'))

        if config_exists:
            st.success("✅ Configuration chargée")

            # Afficher un résumé de la configuration
            with st.expander("Voir le résumé de la configuration"):
                telegram_config = self.config.get('telegram', {})
                portfolio_config = self.config.get('portfolio', [])
                schedule_config = self.config.get('schedule', {})

                st.write("**Telegram:**")
                st.write(
                    f"- Bot Token: {'✅ Configuré' if telegram_config.get('bot_token') else '❌ Non configuré'}")
                st.write(
                    f"- Chat ID: {telegram_config.get('chat_id', 'Non configuré')}")

                st.write("**Portfolio:**")
                st.write(f"- Nombre d'actions: {len(portfolio_config)}")
                if portfolio_config:
                    tickers = [p['ticker'] for p in portfolio_config]
                    st.write(f"- Tickers: {', '.join(tickers)}")

                st.write("**Planification:**")
                execution_times = schedule_config.get('execution_times', [])
                st.write(f"- Heures d'exécution: {', '.join(execution_times)}")
        else:
            st.info(
                "ℹ️ Aucune configuration chargée. Veuillez importer un fichier de configuration.")

        uploaded_file = st.file_uploader(
            "Charger un fichier de configuration JSON",
            type=['json'],
            help="Fichier JSON contenant la configuration Telegram et du portfolio"
        )

        if uploaded_file is not None:
            file_content = uploaded_file.read().decode('utf-8')
            success, message = self.config_manager.load_from_file(file_content)

            if success:
                # Recharger la configuration
                self.config = self.config_manager.get_config()
                st.success(message)
            else:
                st.error(message)

        # Test Telegram (seulement si configuré)
        telegram_config = self.config.get('telegram', {})
        if telegram_config.get('bot_token') and telegram_config.get('chat_id'):
            if st.button("🧪 Tester Telegram"):
                bot = TelegramBot(
                    telegram_config['bot_token'], telegram_config['chat_id'])
                test_data = [{'ticker': 'TEST', 'success': True, 'current_price': 100.0,
                              'gf_value': 95.0, 'valuation': 5.3, 'in_portfolio': True}]
                if bot.send_message(test_data):
                    st.success("Message de test envoyé avec succès!")
                else:
                    st.error("Erreur lors de l'envoi du message de test")

    def _render_scheduler_section(self):
        """Affiche la section du planificateur"""
        # Vérifier si une configuration existe
        if not self.config.get('telegram', {}).get('bot_token'):
            st.warning(
                "⚠️ Configuration Telegram manquante. Importez d'abord une configuration.")
            return

        current_times = self.config.get('schedule', {}).get(
            'execution_times', ['07:25', '19:35'])

        # Affichage des heures actuelles
        st.markdown("**Heures d'exécution programmées:**")
        for i, time_str in enumerate(current_times):
            st.markdown(f"- {time_str}")

        # Statut du planificateur
        is_running = self.scheduler.is_running()
        status = "🟢 Actif" if is_running else "🔴 Inactif"
        st.markdown(f"**Statut du planificateur:** {status}")

        if is_running:
            st.success(
                "✅ Le bot fonctionne en arrière-plan et continuera même si vous fermez cette page")
            st.markdown(
                f"**Prochaines exécutions:** {', '.join(current_times)}")

        # Contrôle du planificateur
        col1, col2 = st.columns(2)

        with col1:
            if st.button("▶️ Démarrer Bot", disabled=is_running):
                if self._start_background_scheduler():
                    st.success("Planificateur démarré en arrière-plan!")
                    st.rerun()
                else:
                    st.error("Erreur lors du démarrage")

        with col2:
            if st.button("⏹️ Arrêter Bot", disabled=not is_running):
                self.scheduler.stop_scheduler()
                st.success("Planificateur arrêté!")
                st.rerun()

        # Exécution manuelle
        st.markdown("---")
        if st.button("🚀 Exécuter Maintenant"):
            with st.spinner("Analyse en cours..."):
                self._execute_portfolio_analysis()
                st.success(
                    "Analyse terminée! Vérifiez les résultats ci-dessous.")

    def _render_portfolio_section(self):
        """Affiche la section du portfolio"""
        # Vérifier si une configuration existe
        if not self.config.get('portfolio'):
            st.info(
                "ℹ️ Aucun portfolio configuré. Importez d'abord une configuration.")
            return

        # Affichage du portfolio (lecture seule)
        portfolio = self.config.get('portfolio', [])
        print(portfolio)
        if portfolio:
            st.subheader("📊 Portfolio configuré")

            # Convertir en DataFrame pour affichage
            df = pd.DataFrame(portfolio)
            print(df)
            df['Statut'] = df['in_portfolio'].apply(
                lambda x: '✅ Dans portfolio' if x else '❌ Hors portfolio')

            # Afficher le tableau en lecture seule
            display_df = df[['ticker', 'Statut']].rename(
                columns={'ticker': 'Ticker'})
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Statistiques du portfolio
            total_stocks = len(portfolio)
            portfolio_stocks = len(
                [p for p in portfolio if p.get('in_portfolio', False)])

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Actions", total_stocks)
            with col2:
                st.metric("Dans Portfolio", portfolio_stocks)

        # Affichage des dernières données
        if st.session_state.portfolio_data:
            st.subheader("📈 Dernières données récupérées")

            # Convertir en DataFrame pour affichage
            display_data = []
            for item in st.session_state.portfolio_data:
                if item.get('success', False):
                    valuation_color = "🟢" if item.get(
                        'valuation', 0) < 0 else "🔴"
                    display_data.append({
                        'Ticker': item['ticker'],
                        'Prix Actuel': f"${item.get('current_price', 0):.2f}",
                        'Valeur GF': f"${item.get('gf_value', 0):.2f}",
                        'Valorisation': f"{valuation_color} {item.get('valuation', 0):.1f}%",
                        'Portfolio': "✅" if item.get('in_portfolio', False) else "❌"
                    })

            if display_data:
                st.dataframe(pd.DataFrame(display_data),
                             use_container_width=True, hide_index=True)

                # Timestamp de la dernière mise à jour
                if st.session_state.last_execution:
                    st.caption(
                        f"Dernière mise à jour: {st.session_state.last_execution.strftime('%d/%m/%Y à %H:%M')}")
            else:
                st.warning(
                    "Aucune donnée valide récupérée lors de la dernière exécution.")

    def _render_stats_section(self):
        """Affiche la section des statistiques"""
        if st.session_state.portfolio_data:
            successful_data = [
                d for d in st.session_state.portfolio_data if d.get('success', False)]

            if successful_data:
                # Statistiques générales
                total_stocks = len(successful_data)
                portfolio_stocks = len(
                    [d for d in successful_data if d.get('in_portfolio', False)])

                st.metric("Total Actions", total_stocks)
                st.metric("Dans Portfolio", portfolio_stocks)

                # Valorisation moyenne
                valuations = [d.get('valuation', 0) for d in successful_data if d.get(
                    'valuation') is not None]
                if valuations:
                    avg_valuation = sum(valuations) / len(valuations)
                    st.metric("Valorisation Moyenne", f"{avg_valuation:.1f}%")

                # Actions sous-évaluées
                undervalued = len([v for v in valuations if v < 0])
                st.metric("Actions Sous-évaluées", undervalued)

        # Dernière exécution
        if st.session_state.last_execution:
            st.metric("Dernière Exécution",
                      st.session_state.last_execution.strftime('%H:%M'))

    def _render_logs_section(self):
        """Affiche la section des logs"""
        if st.button("Rafraîchir les logs"):
            st.rerun()

        try:
            if os.path.exists('gurufocus_bot.log'):
                with open('gurufocus_bot.log', 'r') as f:
                    logs = f.read()

                # Afficher les dernières lignes
                log_lines = logs.split('\n')[-20:]  # 20 dernières lignes
                st.text_area("Logs récents", '\n'.join(log_lines), height=200)
            else:
                st.info("Aucun fichier de log trouvé")
        except Exception as e:
            st.error(f"Erreur lors de la lecture des logs: {e}")

    def _start_background_scheduler(self) -> bool:
        """Démarre le planificateur en arrière-plan"""
        try:
            execution_times = self.config.get(
                'schedule', {}).get('execution_times', [])
            if not execution_times:
                st.error("Aucune heure d'exécution configurée")
                return False

            # Vérifier la configuration Telegram
            telegram_config = self.config.get('telegram', {})
            if not telegram_config.get('bot_token') or not telegram_config.get('chat_id'):
                st.error("Configuration Telegram incomplète")
                return False

            # Créer une fonction d'exécution qui utilise la configuration cachée
            def execute_with_cached_config():
                self._execute_portfolio_analysis_background()

            self.scheduler.start_scheduler(
                execution_times, execute_with_cached_config, self.config_manager)
            return True

        except Exception as e:
            logging.error(f"Erreur lors du démarrage du planificateur: {e}")
            return False

    def _execute_portfolio_analysis_background(self):
        """Exécute l'analyse du portfolio en arrière-plan avec la config cachée"""
        try:
            logging.info("Début de l'analyse du portfolio (arrière-plan)")

            # Récupérer la configuration depuis le cache
            current_config = self.config_manager.get_config()
            portfolio = current_config.get('portfolio', [])

            if not portfolio:
                logging.warning("Aucun ticker dans le portfolio")
                return

            # Récupérer les données
            portfolio_data = []
            for stock in portfolio:
                ticker = stock['ticker']
                data = self.guru_api.get_stock_data(ticker)
                data['in_portfolio'] = stock.get('in_portfolio', False)
                portfolio_data.append(data)
                time.sleep(1)  # Pause entre les requêtes

            # Envoyer via Telegram
            telegram_config = current_config.get('telegram', {})
            if telegram_config.get('bot_token') and telegram_config.get('chat_id'):
                bot = TelegramBot(
                    telegram_config['bot_token'], telegram_config['chat_id'])
                bot.send_message(portfolio_data)

            logging.info(
                "Analyse du portfolio terminée avec succès (arrière-plan)")

        except Exception as e:
            logging.error(
                f"Erreur lors de l'analyse du portfolio (arrière-plan): {e}")

    def _execute_portfolio_analysis(self):
        """Exécute l'analyse du portfolio pour l'interface utilisateur"""
        try:
            logging.info("Début de l'analyse du portfolio (interface)")

            portfolio = self.config.get('portfolio', [])
            if not portfolio:
                st.warning("Aucun ticker dans le portfolio")
                return

            # Récupérer les données
            portfolio_data = []
            for stock in portfolio:
                ticker = stock['ticker']
                data = self.guru_api.get_stock_data(ticker)
                data['in_portfolio'] = stock.get('in_portfolio', False)
                portfolio_data.append(data)
                time.sleep(1)  # Pause entre les requêtes

            # Sauvegarder les données pour l'interface
            st.session_state.portfolio_data = portfolio_data
            st.session_state.last_execution = datetime.now()

            # Envoyer via Telegram
            telegram_config = self.config.get('telegram', {})
            if telegram_config.get('bot_token') and telegram_config.get('chat_id'):
                bot = TelegramBot(
                    telegram_config['bot_token'], telegram_config['chat_id'])
                bot.send_message(portfolio_data)

            logging.info(
                "Analyse du portfolio terminée avec succès (interface)")

        except Exception as e:
            logging.error(
                f"Erreur lors de l'analyse du portfolio (interface): {e}")
            st.error(f"Erreur lors de l'analyse: {e}")


def main():
    """Fonction principale"""
    app = GuruFocusApp()
    app.run()


if __name__ == "__main__":
    main()
