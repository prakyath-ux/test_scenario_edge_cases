# recorder.py - Subprocess version for Streamlit
# Takes URL and format as command line arguments
# Runs until terminated by parent process

import sys
import json
import csv 
import time
import signal
from datetime import datetime
from playwright.sync_api import sync_playwright


# storage for captured data
captured_xpaths = {}

#global variables for cleanup() to access
url = ""
formats = []
output_dir = "."
live_capture_file = None

XPATH_JS = """
(function () {
    // Highlight styles
    const HIGHLIGHT_STYLE = '2px solid red';
    const HIGHLIGHT_BG = 'rgba(255, 0, 0, 0.1)';
    let lastHighlighted = null;
    let originalStyles = {};

    function countMatches(xpath) {
        try {
            const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
            return result.snapshotLength;
        } catch (e) {
            return 0;
        }
    }

    function getAbsoluteXPath(element) {
        if (element === document.body) {
            return '/html/body';
        }

        let position = 1;
        let siblings = element.parentNode ? element.parentNode.childNodes : [];

        for (let sibling of siblings) {
            if (sibling === element) {
                const parentPath = element.parentNode ? getAbsoluteXPath(element.parentNode) : '';
                const tagName = element.tagName.toLowerCase();
                return parentPath + '/' + tagName + '[' + position + ']';
            }
            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                position++;
            }
        }
        return '';
    }

    function getXPath(element) {
        const tag = element.tagName.toLowerCase();
        const text = element.textContent ? element.textContent.trim().slice(0, 30) : '';
        let xpath = '';

        // 1. Try ID (highest priority)
        if (element.id) {
            xpath = '//*[@id="' + element.id + '"]';
            if (countMatches(xpath) === 1) return { xpath, strategy: 'id' };
        }

        // 2. Try name attribute
        if (element.name) {
            xpath = '//' + tag + '[@name="' + element.name + '"]';
            if (countMatches(xpath) === 1) return { xpath, strategy: 'name' };
        }

        // 3. Try data-testid
        if (element.dataset && element.dataset.testid) {
            xpath = '//*[@data-testid="' + element.dataset.testid + '"]';
            if (countMatches(xpath) === 1) return { xpath, strategy: 'data-testid' };

            // Try data-testid + text
            if (text) {
                xpath = '//*[@data-testid="' + element.dataset.testid + '" and contains(., "' + text + '")]';
                if (countMatches(xpath) === 1) return { xpath, strategy: 'data-testid+text' };
            }
        }

        // 4. Try aria-label (accessibility attribute)
        const ariaLabel = element.getAttribute('aria-label');
        if (ariaLabel) {
            xpath = '//*[@aria-label="' + ariaLabel + '"]';
            if (countMatches(xpath) === 1) return { xpath, strategy: 'aria-label' };
        }

        // 5. Try role attribute
        const role = element.getAttribute('role');
        if (role) {
            xpath = '//*[@role="' + role + '"]';
            if (countMatches(xpath) === 1) return { xpath, strategy: 'role' };

            // Try role + text
            if (text) {
                xpath = '//*[@role="' + role + '" and contains(., "' + text + '")]';
                if (countMatches(xpath) === 1) return { xpath, strategy: 'role+text' };
            }
        }

        // 6. Try placeholder
        if (element.placeholder) {
            xpath = '//input[@placeholder="' + element.placeholder + '"]';
            if (countMatches(xpath) === 1) return { xpath, strategy: 'placeholder' };
        }

        // 7. Try type attribute (for inputs/buttons)
        if (element.type && (tag === 'input' || tag === 'button')) {
            xpath = '//' + tag + '[@type="' + element.type + '"]';
            if (countMatches(xpath) === 1) return { xpath, strategy: 'type' };

            // Try type + name or placeholder
            if (element.name) {
                xpath = '//' + tag + '[@type="' + element.type + '" and @name="' + element.name + '"]';
                if (countMatches(xpath) === 1) return { xpath, strategy: 'type+name' };
            }
        }

        // 8. Try href for links
        if (tag === 'a' && element.href) {
            const href = element.getAttribute('href');
            if (href && !href.startsWith('javascript:')) {
                xpath = '//a[@href="' + href + '"]';
                if (countMatches(xpath) === 1) return { xpath, strategy: 'href' };
            }
        }

        // 9. Try class (less reliable but sometimes useful)
        if (element.className && typeof element.className === 'string') {
            const classes = element.className.trim().split(/\\s+/);
            // Try first meaningful class (skip common utility classes)
            for (const cls of classes) {
                if (cls.length > 3 && !cls.match(/^(mt-|mb-|px-|py-|flex|grid|text-|bg-)/)) {
                    xpath = '//' + tag + '[contains(@class, "' + cls + '")]';
                    if (countMatches(xpath) === 1) return { xpath, strategy: 'class' };
                }
            }
        }

        // 10. Try text alone
        if (text && text.length < 50) {
            xpath = '//' + tag + '[contains(., "' + text + '")]';
            if (countMatches(xpath) === 1) return { xpath, strategy: 'text' };
        }

        // 11. No unique relative path found - use absolute
        return { xpath: getAbsoluteXPath(element), strategy: 'absolute' };
    }

    function highlightElement(el) {
        if (lastHighlighted && lastHighlighted !== el) {
            // Restore previous element
            lastHighlighted.style.outline = originalStyles.outline || '';
            lastHighlighted.style.backgroundColor = originalStyles.bg || '';
        }

        if (el) {
            // Save original styles
            originalStyles = {
                outline: el.style.outline,
                bg: el.style.backgroundColor
            };
            // Apply highlight
            el.style.outline = HIGHLIGHT_STYLE;
            el.style.backgroundColor = HIGHLIGHT_BG;
            lastHighlighted = el;
        }
    }

    // Hover highlight
    document.addEventListener('mouseover', function(e) {
        highlightElement(e.target);
    }, true);

    // Click capture
    document.addEventListener('click', function(e) {
        const el = e.target;
        const result = getXPath(el);
        const label = el.id || el.name || el.placeholder || el.textContent.trim().slice(0, 30) || el.tagName.toLowerCase();
        const matches = countMatches(result.xpath);

        window.reportXPath(label, result.xpath, result.strategy, matches, 'click', '');
    }, true);

    // Change capture
   document.addEventListener('change', function(e) {
    const el = e.target;
    const result = getXPath(el);
    const label = el.id || el.name || el.placeholder || el.tagName.toLowerCase();
    const matches = countMatches(result.xpath);
    const value = el.type === 'checkbox' ? el.checked : el.value;
    window.reportXPath(label, result.xpath, result.strategy, matches, 'Input', value);
    }, true);

})();
"""

# receives data from JS via window.reportXPath, stores in global {}
# def handle_xpath(label, xpath, strategy, matches,action, values):
#     key = f"{xpath}|{action}"
#     is_update = key in captured_xpaths

#     captured_xpaths[key] = {
#         "label": label,
#         "xpath": xpath,
#         "strategy": strategy,
#         "matches": matches,
#         "action": action,
#         "values": values
#     }

#     if is_update:
#         print(f"[UPDATE] {label}: {values}", flush=True)
#     else:
#         status = "UNIQUE" if matches == 1 else f"{matches} matches"
#         print(f"[{len(captured_xpaths)}] {label} | {action} | {status}", flush=True)

def handle_xpath(label, xpath, strategy, matches, action, values):
    global live_capture_file
    key = f"{xpath}|{action}"
    is_update = key in captured_xpaths

    captured_xpaths[key] = {
        "label": label,
        "xpath": xpath,
        "strategy": strategy,
        "matches": matches,
        "action": action,
        "values": values
    }

    # write to live capture file for real-time viewing
    if live_capture_file:
        entry = {
            "type": "xpath",
            "label": label,
            "xpath": xpath,
            "strategy": strategy,
            "matches": matches,
            "action": action,
            "values": values,
            "timestamp": datetime.now().isoformat()
        }

        with open(live_capture_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    if is_update:
        print(f"[UPDATE] {label}: {values}", flush=True)
    else:
        status = "UNIQUE" if matches == 1 else f"{matches} matches"
        print(f"[{len(captured_xpaths)}] {label} | {action} | {status}", flush=True)


def save_python(filename, url):
    with open(filename, 'w') as f:
        f.write(f"# XPaths captured from: {url}\n")
        f.write(f"# Captured at: {datetime.now().isoformat()}\n")
        f.write(f"# Total elements: {len(captured_xpaths)}\n\n")
        f.write('XPATHS = {\n')
        for item in captured_xpaths.values():
            xpath_escaped = item["xpath"].replace("'", "\\'")
            f.write(f'    "{item["label"]}_{item["action"]}": \'{xpath_escaped}\',  # {item["strategy"]} | {item["values"]}\n')
        f.write('}\n')

def save_json(filename, url):
    data = {
        "url": url,
        "captured_at": datetime.now().isoformat(),
        "total_elements": len(captured_xpaths),
        "xpaths": list(captured_xpaths.values()) 
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


def save_csv(filename, url):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Label', 'XPath', 'Strategy', 'Matches', 'Action', 'Value'])
        for item in captured_xpaths.values():
            writer.writerow([item["label"], item["xpath"], item["strategy"], item["matches"], item["action"], item["values"]])

# the SIGTERM handler that saves files when streamlit stops the recorder
def cleanup(signum=None, frame=None):
    global url, formats, output_dir
    print("STOPPING...", flush=True)

    if captured_xpaths:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if 'json' in formats:
            filename = f"{output_dir}/xpaths_{timestamp}.json"
            save_json(filename, url)
            print(f"Saved: {filename}", flush=True)
        
        if 'csv' in formats:
            filename = f"{output_dir}/xpaths_{timestamp}.csv"
            save_csv(filename, url)
            print(f"Saved: {filename}", flush=True)
        
        if 'py' in formats:
            filename = f"{output_dir}/xpaths_{timestamp}.py"
            save_python(filename, url)
            print(f"Saved: {filename}", flush=True)
        
        print(f"Total: {len(captured_xpaths)} elements", flush=True)
    else:
        print("No elements captured.", flush=True)
    
    print("DONE", flush=True)
    sys.exit(0)

def main():
    global url, formats, output_dir, live_capture_file

    if len(sys.argv) < 3:
        print("Usage: python recorder.py <url> <formats> [output_dir]", flush=True)
        print("Formats: py,json,csv (comma-seperated)", flush=True)
        sys.exit(1)

    url = sys.argv[1]
    formats = sys.argv[2].split(',')
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "."

    live_capture_file = sys.argv[4] if len(sys.argv) > 4 else None
    #write start marker to live file
    if live_capture_file:
        with open(live_capture_file, 'w') as f:
            f.write(json.dumps({
                "type": "start",
                "url": url,
                "timestamp": datetime.now().isoformat()
            }) + '\n')

    print(f"STARTING: {url}", flush=True)

    #Handle termintion signals
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.expose_function("reportXPath", handle_xpath)
            page.goto(url)
            page.evaluate(XPATH_JS)

            print("RECORDING", flush=True)

            # Keep running until terminated - use page.wait_for_timeout to allow event processing
            while True:
                page.wait_for_timeout(500)

    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        cleanup()

if __name__ == "__main__":
    main()
