# main.py
"""
Playwright visitor simulator
- parallel sessions (CONCURRENCY)
- large pool of user agents (devices) and referrers
- realistic behavior: initial load, 60-70s dwell per page split into scroll segments,
  occasional internal clicks (1-2), randomized UA/referrer per session
Usage (on GitHub Actions runner this will run as provided):
  pip install playwright
  python -m playwright install chromium
  python main.py
"""
import asyncio
import random
import time
from typing import List, Optional
from playwright.async_api import async_playwright

# -----------------------
# CONFIG
# -----------------------
TARGET_PAGES = [
    "https://rozgartechpk.blogspot.com/",
    "https://rozgartechpk.blogspot.com/p/about-us",
    "https://rozgartechpk.blogspot.com/2025/09/blog-post.html",
    "https://rozgartechpk.blogspot.com/2025/09/top-10-online-jobs-for-students-in-2026.html",
    "https://rozgartechpk.blogspot.com/2025/09/blog-post.html",
]

# Default concurrency (parallel browser sessions per runner)
CONCURRENCY = int(__import__("os").environ.get("CONCURRENCY", 3))

# dwell time per page (seconds)
PAGE_DWELL_MIN = 60
PAGE_DWELL_MAX = 70

# how many pages in a session (2-3 is recommended)
PAGES_PER_SESSION_MIN = 2
PAGES_PER_SESSION_MAX = 3

# headless or visible
HEADLESS = True

# -----------------------
# LARGE USER AGENT POOL
# (desktop, mobile, tablets, older and new)
# -----------------------
USER_AGENTS = [
    # Desktop Chrome / Edge / Firefox / Safari
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/118.0.5993.117 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.5845.140 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:117.0) Gecko/20100101 Firefox/117.0",

    # Mobile Android
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 Chrome/118.0.5993 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/117.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 Chrome/116.0.5845 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; OnePlus) AppleWebKit/537.36 Chrome/115.0.0.0 Mobile Safari/537.36",

    # iPhone / iPad
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 16_4 like Mac OS X) AppleWebKit/605.1.15 Version/16.0 Mobile/15E148 Safari/604.1",

    # Older / less common
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",  # keep but low probability
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
]

# -----------------------
# EXTENSIVE REFERRER POOL
# -----------------------
REFERRERS = [
    # Search engines
    "https://www.google.com/search?q=rozgartech",
    "https://www.bing.com/search?q=rozgartechpk",
    "https://search.yahoo.com/search?p=rozgartech",
    "https://duckduckgo.com/?q=rozgartech",
    "https://www.baidu.com/s?wd=rozgartech",
    "https://yandex.com/search/?text=rozgartech",
    "https://www.google.com/search?q=rozgartechpkblog",
    "https://www.bing.com/search?q=rozgartechpk",
    "https://search.yahoo.com/search?p=rozgartech",
    "https://duckduckgo.com/?q=rozgartechpk",
    "https://www.baidu.com/s?wd=rozgartech+blog",
    "https://yandex.com/search/?text=rozgartech+free",


    # Social networks
    "https://www.facebook.com/",
    "https://m.facebook.com/",
    "https://twitter.com/",
    "https://t.co/",
    "https://www.reddit.com/",
    "https://www.linkedin.com/",
    "https://www.instagram.com/",
    "https://www.pinterest.com/",

    # News/blogs/forums
    "https://news.ycombinator.com/",
    "https://medium.com/",
    "https://dev.to/",
    "https://www.producthunt.com/",
    "https://www.quora.com/",
    "https://stackoverflow.com/",
    "https://www.tumblr.com/",

    # Short links / aggregators
    "https://bit.ly/rozgartechpk",
    "https://tinyurl.com/blog+rozgartech",
    "https://lnkd.in/rozgartechpk",
    "",  # direct
]

# -----------------------
# Helper behavior functions
# -----------------------
async def scroll_and_wait(page, total_seconds: float):
    """Break total_seconds into segments, scroll and occasionally move mouse."""
    segments = random.randint(3, 6)
    per = total_seconds / segments
    for _ in range(segments):
        # scroll by a portion of viewport
        try:
            await page.evaluate(
                """() => {
                    const step = Math.floor(window.innerHeight * (0.25 + Math.random()*0.6));
                    window.scrollBy({ top: step, behavior: 'smooth' });
                }"""
            )
        except Exception:
            pass
        # small random pause
        await asyncio.sleep(per * random.uniform(0.9, 1.1))
        # occasional mouse move
        if random.random() < 0.35:
            try:
                box = await page.evaluate("() => ({w: window.innerWidth, h: window.innerHeight})")
                x = int(box["w"] * random.random())
                y = int(box["h"] * random.random())
                await page.mouse.move(x, y, steps=random.randint(6, 18))
            except Exception:
                pass

async def visit_single_session(playwright, session_index: int, proxy: Optional[str]):
    """
    One browser session:
    - random UA, referrer, viewport
    - visits 2-3 pages, stays 60-70s per page, scrolls, clicks internal links occasionally
    - proxy param is optional (like 'http://IP:PORT' or 'socks5://127.0.0.1:9050')
    """
    browser_type = playwright.chromium
    launch_args = {"headless": HEADLESS}
    if proxy:
        # Playwright expects proxy dict: {"server": proxy}
        launch_args["proxy"] = {"server": proxy}

    browser = await browser_type.launch(**launch_args)
    try:
        # pick UA and viewport; some UAs in list are strings only so handle both tuple and string cases
        ua = random.choice(USER_AGENTS)
        viewport = {"width": 1366, "height": 768}
        # if UA tuple structure (ua_str, (w,h)) then unpack; else keep defaults
        if isinstance(ua, tuple):
            ua_str, vp = ua
            ua = ua_str
            viewport = {"width": vp[0], "height": vp[1]}

        context = await browser.new_context(user_agent=ua, viewport=viewport)
        page = await context.new_page()

        # pages per session
        pages_to_visit = random.randint(PAGES_PER_SESSION_MIN, PAGES_PER_SESSION_MAX)
        current_page = random.choice(TARGET_PAGES)

        for pnum in range(pages_to_visit):
            ref = random.choice(REFERRERS)
            # sometimes simulate click-through from ref
            if ref and random.random() < 0.55:
                # try to go to ref briefly then go to target (mimic search click)
                try:
                    await page.goto(ref, wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(random.uniform(0.6, 2.0))
                    await page.goto(current_page, wait_until="load", timeout=30000)
                except Exception:
                    # fallback: direct goto with referer header
                    try:
                        await context.set_extra_http_headers({"referer": ref})
                        await page.goto(current_page, wait_until="load", timeout=30000)
                    except Exception as e:
                        print(f"[session {session_index}] nav failed to {current_page} via ref {ref}: {e}")
                        return
            else:
                try:
                    await page.goto(current_page, wait_until="load", timeout=30000)
                except Exception as e:
                    print(f"[session {session_index}] direct nav failed {current_page}: {e}")
                    return

            print(f"[session {session_index}] loaded {current_page} proxy={proxy} ua={ua[:60]}...")

            # dwell and scroll (60-70s)
            dwell = random.uniform(PAGE_DWELL_MIN, PAGE_DWELL_MAX)
            await scroll_and_wait(page, dwell)

            # try 0-2 internal clicks
            try:
                anchors = await page.query_selector_all("a[href]")
                internal_candidates = []
                for a in anchors:
                    try:
                        href = await a.get_attribute("href")
                        if not href:
                            continue
                        # keep same host or relative links (rough filter)
                        if current_page.split("/")[2] in href or href.startswith("/"):
                            internal_candidates.append((a, href))
                    except Exception:
                        continue
                if internal_candidates and random.random() < 0.7:
                    clicks = random.randint(1, 2)
                    for _ in range(clicks):
                        el, href = random.choice(internal_candidates)
                        try:
                            await el.click(timeout=5000)
                            await asyncio.sleep(random.uniform(1.0, 2.8))
                            # dwell again after click
                            await scroll_and_wait(page, random.uniform(PAGE_DWELL_MIN, PAGE_DWELL_MAX))
                            # set current page to new location if possible
                            try:
                                new_url = page.url
                                if new_url:
                                    current_page = new_url
                            except Exception:
                                pass
                        except Exception:
                            # fallback to direct navigation
                            try:
                                target = href if href.startswith("http") else (f"https://{current_page.split('/')[2]}{href}")
                                await page.goto(target, wait_until="load", timeout=20000)
                                await asyncio.sleep(random.uniform(1.0, 2.5))
                                await scroll_and_wait(page, random.uniform(PAGE_DWELL_MIN, PAGE_DWELL_MAX))
                                current_page = page.url
                            except Exception:
                                pass
            except Exception:
                pass

            # small pause before next page selection
            await asyncio.sleep(random.uniform(1.5, 3.5))
            # choose next page probabilistically
            if random.random() < 0.6:
                # move to another target page
                current_page = random.choice(TARGET_PAGES)
            else:
                # maybe end session early
                if random.random() < 0.25:
                    break

        await context.close()
        print(f"[session {session_index}] finished (proxy={proxy})")
    finally:
        await browser.close()

async def run_many_sessions(proxies: Optional[List[str]] = None):
    """
    Run multiple sessions in parallel. If `proxies` provided, one proxy is used per session where possible.
    """
    sem = asyncio.Semaphore(CONCURRENCY)
    session_counter = 0

    async with async_playwright() as playwright:
        async def worker(proxy_for_this):
            nonlocal session_counter
            async with sem:
                session_counter += 1
                sid = session_counter
                try:
                    await visit_single_session(playwright, sid, proxy_for_this)
                except Exception as e:
                    print(f"[session {sid}] exception: {e}")

        tasks = []
        # decide how many sessions to launch this run: equal to CONCURRENCY
        if proxies:
            # tie proxies to sessions (up to concurrency)
            chosen = random.sample(proxies, min(len(proxies), CONCURRENCY))
            for p in chosen:
                tasks.append(asyncio.create_task(worker(p)))
            # if not enough proxies for concurrency, add direct sessions
            while len(tasks) < CONCURRENCY:
                tasks.append(asyncio.create_task(worker(None)))
        else:
            for _ in range(CONCURRENCY):
                tasks.append(asyncio.create_task(worker(None)))

        await asyncio.gather(*tasks)

if __name__ == "__main__":
    # If you want to provide proxies, put them in proxies.txt (one per line) in repo, same formats:
    # http://IP:PORT or socks5://127.0.0.1:9050
    try:
        proxies = []
        try:
            with open("proxies.txt", "r", encoding="utf-8") as f:
                proxies = [l.strip() for l in f if l.strip()]
        except Exception:
            proxies = []
        print("Starting Playwright simulator; concurrency:", CONCURRENCY)
        asyncio.run(run_many_sessions(proxies if proxies else None))
    except KeyboardInterrupt:
        print("Stopped by user")
