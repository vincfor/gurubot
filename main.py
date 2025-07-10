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
    """Gestionnaire de configuration"""

    def __init__(self):
        self.config_file = "config.json"
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

    def load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return self.default_config
        except Exception as e:
            logging.error(
                f"Erreur lors du chargement de la configuration: {e}")
            return self.default_config

    def save_config(self, config):
        """Sauvegarde la configuration dans le fichier JSON"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(
                f"Erreur lors de la sauvegarde de la configuration: {e}")
            return False


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
                position = "✅" if item.get('in_portfolio', True) else "❌"

                line = f"\n{ticker:<11} | {prix:>7} | {gf_val:>7} | {valuation:>6} | {position}"
                table += line

        table += "\n</pre>\n\n"
        return table


class SchedulerManager:
    """Gestionnaire de planification"""

    def __init__(self):
        self.running = False
        self.thread = None
        self.schedule_times = []

    def start_scheduler(self, execution_times: list, callback_func):
        """Démarre le planificateur"""
        if self.running:
            self.stop_scheduler()

        # Nettoyer les anciens jobs
        schedule.clear()

        # Programmer les nouveaux jobs
        for time_str in execution_times:
            schedule.every().day.at(time_str).do(callback_func)

        self.schedule_times = execution_times
        self.running = True

        # Démarrer le thread
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()

        logging.info(
            f"Planificateur démarré - Exécution quotidienne à {execution_times}")

    def stop_scheduler(self):
        """Arrête le planificateur"""
        self.running = False
        schedule.clear()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
        logging.info("Planificateur arrêté")

    def _run_scheduler(self):
        """Boucle principale du planificateur"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Vérification toutes les minutes


class GuruFocusApp:
    """Application principale"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.guru_api = GuruFocusAPI()
        self.scheduler = SchedulerManager()
        self.telegram_bot = None

        # Initialiser le state
        if 'config' not in st.session_state:
            st.session_state.config = self.config_manager.load_config()

        if 'scheduler_running' not in st.session_state:
            st.session_state.scheduler_running = False

        if 'last_execution' not in st.session_state:
            st.session_state.last_execution = None

        if 'portfolio_data' not in st.session_state:
            st.session_state.portfolio_data = []

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
        st.subheader("Fichier de configuration")

        uploaded_file = st.file_uploader(
            "Charger un fichier de configuration JSON",
            type=['json'],
            help="Fichier JSON contenant la configuration Telegram et du portfolio"
        )

        if uploaded_file is not None:
            try:
                config_data = json.load(uploaded_file)
                st.session_state.config = config_data
                self.config_manager.save_config(config_data)
                st.success("Configuration chargée avec succès!")
            except Exception as e:
                st.error(f"Erreur lors du chargement: {e}")

        # Configuration
        telegram_token = st.session_state.config.get(
            'telegram', {}).get('bot_token', '')

        telegram_chat_id = st.session_state.config.get(
            'telegram', {}).get('chat_id', '')

        if st.button("Sauvegarder Configuration"):
            self.config_manager.save_config(st.session_state.config)
            st.success("Configuration Telegram sauvegardée!")

        # Test Telegram
        if st.button("Tester Telegram"):
            if telegram_token and telegram_chat_id:
                bot = TelegramBot(telegram_token, telegram_chat_id)
                test_data = [{'ticker': 'TEST', 'success': True, 'current_price': 100.0,
                              'gf_value': 95.0, 'valuation': 5.3, 'in_portfolio': True}]
                if bot.send_message(test_data):
                    st.success("Message de test envoyé avec succès!")
                else:
                    st.error("Erreur lors de l'envoi du message de test")
            else:
                st.error("Veuillez saisir le token et le chat ID")

    def _render_scheduler_section(self):
        """Affiche la section du planificateur"""
        current_times = st.session_state.config.get(
            'schedule', {}).get('execution_times', ['07:25', '19:35'])

        # Modification des heures
        new_times = []
        for i, time_str in enumerate(current_times):
            new_time = st.time_input(
                f"Heure {i+1}", value=datetime.strptime(time_str, '%H:%M').time())
            new_times.append(new_time.strftime('%H:%M'))

        # Ajouter une nouvelle heure
        if st.button("Ajouter une heure"):
            new_times.append("12:00")

        # Supprimer la dernière heure
        if len(new_times) > 1 and st.button("Supprimer dernière heure"):
            new_times.pop()

        # Sauvegarder les heures
        if st.button("Sauvegarder Horaires"):
            st.session_state.config['schedule']['execution_times'] = new_times
            self.config_manager.save_config(st.session_state.config)
            st.success("Horaires sauvegardés!")

        # Contrôle du planificateur
        col1, col2 = st.columns(2)

        with col1:
            if st.button("▶️ Démarrer", disabled=st.session_state.scheduler_running):
                if self._start_scheduler():
                    st.session_state.scheduler_running = True
                    st.success("Planificateur démarré!")
                else:
                    st.error("Erreur lors du démarrage")

        with col2:
            if st.button("⏹️ Arrêter", disabled=not st.session_state.scheduler_running):
                self.scheduler.stop_scheduler()
                st.session_state.scheduler_running = False
                st.success("Planificateur arrêté!")

        # Statut
        status = "🟢 Actif" if st.session_state.scheduler_running else "🔴 Inactif"
        st.markdown(f"**Statut:** {status}")

        if st.session_state.scheduler_running:
            st.markdown(f"**Prochaines exécutions:** {', '.join(new_times)}")

        # Exécution manuelle
        if st.button("🚀 Exécuter Maintenant"):
            self._execute_portfolio_analysis()

    def _render_portfolio_section(self):
        """Affiche la section du portfolio"""
        # Gestion du portfolio
        portfolio = st.session_state.config.get('portfolio', [])

        # Ajouter un nouveau ticker
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            new_ticker = st.text_input(
                "Nouveau ticker", placeholder="Ex: AAPL").upper()

        with col2:
            in_portfolio = st.checkbox("Dans le portfolio", value=True)

        with col3:
            if st.button("Ajouter"):
                if new_ticker and new_ticker not in [p['ticker'] for p in portfolio]:
                    portfolio.append(
                        {'ticker': new_ticker, 'in_portfolio': in_portfolio})
                    st.session_state.config['portfolio'] = portfolio
                    self.config_manager.save_config(st.session_state.config)
                    st.success(f"Ticker {new_ticker} ajouté!")
                    st.rerun()

        # Affichage du portfolio
        if portfolio:
            df = pd.DataFrame(portfolio)
            edited_df = st.data_editor(
                df,
                column_config={
                    "ticker": st.column_config.TextColumn("Ticker", disabled=True),
                    "in_portfolio": st.column_config.CheckboxColumn("Dans le portfolio")
                },
                hide_index=True,
                use_container_width=True
            )

            # Sauvegarder les modifications
            if st.button("Sauvegarder Portfolio"):
                st.session_state.config['portfolio'] = edited_df.to_dict(
                    'records')
                self.config_manager.save_config(st.session_state.config)
                st.success("Portfolio sauvegardé!")

        # Affichage des dernières données
        if st.session_state.portfolio_data:
            st.subheader("Dernières données récupérées")

            # Convertir en DataFrame pour affichage
            display_data = []
            for item in st.session_state.portfolio_data:
                if item.get('success', False):
                    display_data.append({
                        'Ticker': item['ticker'],
                        'Prix Actuel': f"${item.get('current_price', 0):.2f}",
                        'Valeur GF': f"${item.get('gf_value', 0):.2f}",
                        'Valorisation': f"{item.get('valuation', 0):.1f}%",
                        'Dans Portfolio': "✅" if item.get('in_portfolio', False) else "❌"
                    })

            if display_data:
                st.dataframe(pd.DataFrame(display_data),
                             use_container_width=True)

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

    def _start_scheduler(self) -> bool:
        """Démarre le planificateur"""
        try:
            execution_times = st.session_state.config.get(
                'schedule', {}).get('execution_times', [])
            if not execution_times:
                st.error("Aucune heure d'exécution configurée")
                return False

            # Vérifier la configuration Telegram
            telegram_config = st.session_state.config.get('telegram', {})
            if not telegram_config.get('bot_token') or not telegram_config.get('chat_id'):
                st.error("Configuration Telegram incomplète")
                return False

            self.scheduler.start_scheduler(
                execution_times, self._execute_portfolio_analysis)
            return True

        except Exception as e:
            logging.error(f"Erreur lors du démarrage du planificateur: {e}")
            return False

    def _execute_portfolio_analysis(self):
        """Exécute l'analyse du portfolio"""
        try:
            logging.info("Début de l'analyse du portfolio")

            portfolio = st.session_state.config.get('portfolio', [])
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

            # Sauvegarder les données
            st.session_state.portfolio_data = portfolio_data
            st.session_state.last_execution = datetime.now()

            # Envoyer via Telegram
            telegram_config = st.session_state.config.get('telegram', {})
            if telegram_config.get('bot_token') and telegram_config.get('chat_id'):
                bot = TelegramBot(
                    telegram_config['bot_token'], telegram_config['chat_id'])
                bot.send_message(portfolio_data)

            logging.info("Analyse du portfolio terminée avec succès")

        except Exception as e:
            logging.error(f"Erreur lors de l'analyse du portfolio: {e}")


def main():
    """Fonction principale"""
    app = GuruFocusApp()
    app.run()


if __name__ == "__main__":
    main()
