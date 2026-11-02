"""What the LG (webos/build.py) and Samsung (tizen/build.py) packages share: the settings and the web app's files.

The settings come from config.properties, the same file as the Android build. --generic leaves it out (the GitHub
release is built that way): no TMDB key, and the TV's time zone picks the city, the currency and the region.
"""
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import translate  # noqa: E402  (the catalogues and the keys the web app uses)

GENERIC = {'tmdbKey': '', 'tmdbRegion': '', 'latitude': '', 'longitude': '', 'city': '', 'language': 'auto',
           'currency': '', 'temperature': 'auto', 'theme': 'auto', 'showCrypto': True, 'hideAnimation': False, 'hideApps': [],
           'shelfApps': [], 'drawerFirst': False, 'openPicksIn': 'apps', 'clock24': True, 'glassBlur': False, 'photos': True,
           'inputs': []}


def config_from_args(args):
    """The settings for these command-line arguments (--generic, --config PATH or config.properties)."""
    if '--generic' in args:
        return dict(GENERIC)
    path = os.path.join(ROOT, 'config.properties')
    if '--config' in args:
        path = os.path.abspath(args[args.index('--config') + 1])
    return read_config(path)


def read_config(path):
    if not os.path.exists(path):
        shutil.copy(os.path.join(ROOT, 'config.example.properties'), path)
        print('Created config.properties: add your TMDB key and your city there (optional), then build again.')
    values = {}
    try:
        with open(path, encoding='utf-8-sig') as f:
            lines = f.readlines()
    except UnicodeDecodeError:   # Notepad's "Unicode" is UTF-16
        sys.exit('config.properties is saved as UTF-16 (Notepad\'s "Unicode"). Save it as UTF-8 and build again.')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"')

    def number(key, default):
        v = values.get(key, '') or default
        if not re.match(r'^-?\d+(\.\d+)?$', v):
            sys.exit('config.properties: %s must be a number (got "%s")' % (key, v))
        return v

    return {
        'tmdbKey': values.get('tmdb_key', ''),
        'tmdbRegion': values.get('tmdb_region', 'US') or 'US',
        'latitude': number('latitude', '40.7128'),
        'longitude': number('longitude', '-74.0060'),
        'city': values.get('city', ''),
        'language': values.get('language', 'auto') or 'auto',
        'currency': values.get('currency', 'USD') or 'USD',
        'temperature': values.get('temperature', 'auto') or 'auto',
        'theme': values.get('theme', 'auto') or 'auto',
        'showCrypto': values.get('show_crypto', 'true').lower() != 'false',
        'hideAnimation': values.get('hide_animation', 'false').lower() == 'true',
        'hideApps': [s.strip() for s in values.get('hide_apps', '').split(',') if s.strip()],
        'shelfApps': [s.strip() for s in values.get('shelf_apps', '').split(',') if s.strip()],
        'drawerFirst': values.get('drawer_first', 'false').lower() == 'true',
        'clock24': values.get('clock_24h', 'true').lower() != 'false',
        'glassBlur': values.get('glass_blur', 'false').lower() == 'true',
        'photos': values.get('background_photos', 'true').lower() != 'false',
        'inputs': read_inputs(values.get('inputs', '')),
        'openPicksIn': 'nuvio' if values.get('open_picks_in', '').strip().lower() == 'nuvio' else 'apps',
    }


# couch-inputs: the glyphs in web/inputs (drawn for this app, MIT like the rest), and the words config.properties may use
# for each. Brand names pick a generic glyph, never a logo.
INPUT_ICONS = {
    'hdmi': ('hdmi',),
    'box': ('box', 'streamer', 'streaming', 'appletv', 'apple', 'roku', 'firetv', 'fire', 'chromecast', 'shield', 'mibox'),
    'console': ('console', 'game', 'games', 'gamepad', 'playstation', 'ps4', 'ps5', 'xbox', 'switch', 'nintendo'),
    'cable': ('cable', 'stb', 'settop', 'set-top', 'satellite', 'sat', 'yes', 'hot', 'decoder'),
    'pc': ('pc', 'computer', 'laptop', 'mac', 'desktop', 'monitor'),
    'disc': ('disc', 'bluray', 'blu-ray', 'dvd', 'player'),
    'sound': ('sound', 'soundbar', 'receiver', 'avr', 'speaker', 'audio'),
    'camera': ('camera', 'cam'),
    'antenna': ('antenna', 'tv', 'live', 'tuner', 'aerial'),
}


def input_icon(word):
    w = re.sub(r'[\s_]+', '', word.lower())
    for icon, words in INPUT_ICONS.items():
        if w in words:
            return icon
    return ''


def read_inputs(text):
    """inputs=HDMI1:Apple TV:appletv,HDMI2:PlayStation:console → [{key: 'hdmi1', name: 'Apple TV', icon: 'box'}, ...].

    The source is HDMI1-4 (or TV for the tuner); the name and the icon are optional (the TV's own "HDMI 1" and the HDMI
    glyph). An icon this build doesn't know is an error, so a typo doesn't quietly become the plain one."""
    out = []
    for part in [p.strip() for p in text.split(',') if p.strip()]:
        bits = [b.strip() for b in part.split(':')]
        src = re.sub(r'[\s_-]+', '', bits[0].lower())
        m = re.match(r'^hdmi([1-9])$', src)
        key = 'hdmi' + m.group(1) if m else 'live' if src in ('tv', 'live', 'livetv', 'antenna', 'tuner') else ''
        if not key:
            sys.exit('config.properties: inputs: "%s" isn\'t an input (HDMI1 to HDMI4, or TV)' % bits[0])
        name = bits[1] if len(bits) > 1 else ''
        icon = input_icon(bits[2]) if len(bits) > 2 and bits[2] else ''
        if len(bits) > 2 and bits[2] and not icon:
            sys.exit('config.properties: inputs: no icon "%s" (there are %s)' % (bits[2], ', '.join(INPUT_ICONS)))
        if any(x['key'] == key for x in out):
            continue
        out.append({'key': key, 'name': name, 'icon': icon})
    return out


def coins():
    """The coins' logos from the Android app's vector drawables, as SVG paths (BTC, ETH, SOL, USDT)."""
    out = []
    for name in ('btc', 'eth', 'sol', 'usdt'):
        with open(os.path.join(ROOT, 'app', 'res', 'drawable', 'coin_%s.xml' % name), encoding='utf-8') as f:
            out.append(re.findall(r'android:pathData="([^"]+)"', f.read()))
    return out


def catalogues():
    """Each language's catalogue (app/assets/i18n), with only the keys the web app uses: {lang: {key: text}}."""
    keys = translate.web_keys()
    return {lang: {k: v for k, v in sorted(translate.load(lang).items()) if k in keys} for lang in translate.languages()}


def files(config, made_by):
    """The web app's files, {path inside the app: bytes}: web/, the settings, the catalogues, the app's symbols and font."""
    out = {}
    web = os.path.join(ROOT, 'web')
    for name in sorted(os.listdir(web)):
        if os.path.isdir(os.path.join(web, name)):
            continue
        with open(os.path.join(web, name), 'rb') as f:
            out[name] = f.read()
    photos = os.path.join(web, 'photos')   # calm-photos: the background photos and their CREDITS.txt
    for name in sorted(os.listdir(photos)) if os.path.isdir(photos) else []:
        with open(os.path.join(photos, name), 'rb') as f:
            out['photos/' + name] = f.read()
    fonts = os.path.join(web, 'fonts')   # couch-look: Antonio (SIL OFL 1.1, web/fonts/OFL-Antonio.txt) for the big clock
    for name in sorted(os.listdir(fonts)) if os.path.isdir(fonts) else []:
        with open(os.path.join(fonts, name), 'rb') as f:
            out['fonts/' + name] = f.read()
    glyphs = os.path.join(web, 'inputs')   # couch-inputs: the inputs' glyphs (our own drawings) and their LICENSE.txt
    for name in sorted(os.listdir(glyphs)) if os.path.isdir(glyphs) else []:
        with open(os.path.join(glyphs, name), 'rb') as f:
            out['inputs/' + name] = f.read()
    icons = os.path.join(web, 'icons')
    for name in sorted(os.listdir(icons)):
        with open(os.path.join(icons, name), 'rb') as f:
            out['icons/' + name] = f.read()
    out['config.js'] = ('/* Generated by %s. */\nwindow.CONFIG = %s;\n'
                        % (made_by, json.dumps(config, ensure_ascii=False))).encode('utf-8')
    out['coins.js'] = ('window.COINS = %s;\n' % json.dumps(coins())).encode('utf-8')
    out['i18n.js'] = ('/* Generated by %s from app/assets/i18n. */\nwindow.I18N_CATALOGUES = %s;\n'
                      % (made_by, json.dumps(catalogues(), ensure_ascii=False, separators=(',', ':')))).encode('utf-8')
    symbols = os.path.join(ROOT, 'app', 'assets', 'symbols')
    for name in sorted(os.listdir(symbols)):
        if name.endswith('.png') or name.startswith('LICENSE'):
            with open(os.path.join(symbols, name), 'rb') as f:
                out['symbols/' + name] = f.read()
    for name in ('InterVariable.ttf', 'OFL.txt'):
        with open(os.path.join(ROOT, 'app', 'assets', 'fonts', name), 'rb') as f:
            out['fonts/' + name] = f.read()
    return out


def preview(app, out_dir):
    """Leaves the app's files in out_dir, to open index.html in a browser."""
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    for path, content in app.items():
        target = os.path.join(out_dir, path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as f:
            f.write(content)
