import lvgl as lv
import random
import ujson
import net
import urequests

# ---------- Vobot App Configurations ----------
NAME = "Byte of Wisdom"
ICON: str = "A:apps/programming-quotes/resources/icon.png"
CAN_BE_AUTO_SWITCHED: bool = True

# ---------- Local Configurations ----------
DEBUG: bool = False
API_URL: str = "https://programming-quotes-api-pi.vercel.app/quotes/random"

# ---------- Constants ----------
SCREEN_WIDTH: int = 320
SCREEN_HEIGHT: int = 240
CONTAINER_PADDING: int = 12
MESSAGE_TYPE: dict[str, int] = {
    "INFO": 1,
    "WARN": 2,
    "ERROR": 3,
}
NORMALIZE_REPLACEMENT_MAP: dict[str, str] = {
    "‘": "'",
    "’": "'",
    "–": "-",
    "—": "-",
    "„": '"',
    "“": '"',
    "”": '"'
}

# ---------- Colors ----------
COLOR_JSON_PATH: str = "./apps/programming-quotes/colors.json"
colors: str | None = None

# ---------- Widgets ----------
screen = None

# ---------- Styles ----------
# Container style
container_style = lv.style_t()
container_style.init()
container_style.set_border_width(0)
container_style.set_radius(0)
container_style.set_pad_all(CONTAINER_PADDING)
container_style.set_width(SCREEN_WIDTH)
container_style.set_height(SCREEN_HEIGHT)

# Label style
label_style = lv.style_t()
label_style.init()
label_style.set_width(SCREEN_WIDTH - (CONTAINER_PADDING * 2))
label_style.set_text_color(lv.color_hex(0xFFFFFF))
# label_style.set_text_font(lv.font_ascii_14)

# ---------- Utilities ----------
def dprint(msg: str) -> None:
    """
    Print a debug message to console, if in debug mode.

    Args:
        msg (str): The message to print
    """
    if DEBUG:
        print(msg)

def request(url: str):
    """
    Load JSON response from a given URL.

    Args:
        url (str): The URL to load
    Returns:
        JSON object.

    Raises:
        Exception, if something went wrong loading the API.
    """
    if net.connected():
        dprint(f"Fetching {url}")

        response = urequests.get(url, headers={"Content-Type": "application/json"})

        if response.status_code == 200:
            dprint(f"Got response with status code {response.status_code}")
            return ujson.loads(response.text)
        else:
            raise Exception(f"Failed to load {url}, status code: {response.status_code}, response body: {response.text}")
    else:
        raise Exception(f"Wifi is not connected")

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """
    Converts a hex color to RGB tuple.

    Args:
        hex_color (str): Hex color to convert

    Returns:
        RGB tuple of color to convert.
    """
    hex_color = hex_color.lstrip("#")

    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    elif len(hex_color) == 3:
        r = int(hex_color[0] * 2, 16)
        g = int(hex_color[1] * 2, 16)
        b = int(hex_color[2] * 2, 16)
    else:
        raise ValueError("Invalid hex color format")

    return (r, g, b)

def get_random_color():
    """
    Choose a color from pre-defined color set.

    Returns:
        RGB tuple of color choosen.
    """
    global colors

    random_color = random.choice(colors)
    return hex_to_rgb(random_color)

# ---------- Initialize UI ----------
def make_display_fullscreen_message(level: str = MESSAGE_TYPE["INFO"]) -> function[str]:
    """
    Creates function that display fullscreen message

    Args:
        level (MessageType): Indicates if the message is an error message that should be displayed in red

    Returns:
        None. The message is displayed on the screen.
    """
    def display_fullscreen_message(message: str) -> None:
        global screen

        screen.clean()
        screen.set_style_bg_color(lv.color_hex(0x000000),0)

        message_label = lv.label(screen)
        message_label.add_style(label_style, 0)
        message_label.center()
        message_label.set_long_mode(lv.label.LONG.WRAP)
        message_label.set_style_text_color(lv.color_hex(0xFF0000) if level is MESSAGE_TYPE["ERROR"] else lv.color_hex(0xFFFFFF), 0)
        message_label.set_text(message)

        lv.refr_now(None)

    return display_fullscreen_message

display_error_screen = make_display_fullscreen_message(MESSAGE_TYPE["ERROR"])
display_info_screen = make_display_fullscreen_message(MESSAGE_TYPE["INFO"])

def display_quote(quote, author) -> None:
    """
    Display quote on screen.

    Returns:
        None. Quote is displayed on the screen.
    """
    global screen

    screen.clean()

    # Add Container
    container = lv.obj(screen)
    container.align(lv.ALIGN.CENTER, 0, 0)
    container.add_style(container_style, 0)
    container.set_style_bg_color(lv.color_make(*get_random_color()), 0)

    # Add author
    author_label = lv.label(container)
    author_label.add_style(label_style, 0)
    author_label.align(lv.ALIGN.BOTTOM_LEFT, 0, 0)
    author_label.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)
    author_label.set_text(author if author else "Anonymous")
    author_label.set_style_text_font(lv.font_ascii_14, 0)
    author_label.update_layout()

    # Add quote
    container_height = SCREEN_HEIGHT - author_label.get_height();
    quote_label = lv.label(container)
    quote_label.add_style(label_style, 0)
    quote_label.set_style_height(container_height  - (CONTAINER_PADDING * 3), 0)
    quote_label.set_long_mode(lv.label.LONG.DOT)
    quote_label.align(lv.ALIGN.TOP_LEFT, 0, 0)
    quote_label.set_text(quote)

    lv.refr_now(None)

# ---------- Events ----------
def fetch_and_display_random_quote() -> None:
    """
    Fetch and display a random quote on screen.

    Returns:
        None. A random quote retrieve from API is displayed on the screen.
    """
    try:
        response = request(API_URL)

        # Find and replace known non-ASCII characters to ASCII
        for key in response:
            for old, new in NORMALIZE_REPLACEMENT_MAP.items():
                response[key] = response[key].replace(old, new)

        display_quote(response["en"], response["author"])
    except Exception as e:
        display_error_screen(f"Error occured on start: {e}")

def event_handler(event) -> None:
    """
    Code executed when an event is called.

    Note:
    - This can be some paint events as well. Therefore, check the event code!
    - Don't call a method using "await"! Otherwise, the whole function becomes async!

    See https://docs.lvgl.io/master/overview/event.html for possible events.
    """
    e_code = event.get_code()

    # dprint(f"Got code {e_code}")

    if e_code == lv.EVENT.KEY:
        e_key = event.get_key()
        dprint(f"Got key {e_key}")

        if e_key == lv.KEY.LEFT or e_key == lv.KEY.RIGHT:
            fetch_and_display_random_quote()

# ---------- Lifecycle hooks ----------
async def on_start():
    """
    Code executed on start.

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    global screen, colors

    dprint("on start")

    # Loads color set
    with open(COLOR_JSON_PATH, "r") as file:
        colors = ujson.load(file)

    screen = lv.obj()
    lv.screen_load(screen)

    # Bind input events
    screen.add_event(event_handler, lv.EVENT.ALL, None)
    lv.group_get_default().add_obj(screen)
    lv.group_focus_obj(screen)
    lv.group_get_default().set_editing(True)

    display_info_screen("Loading...")

    # Initial fetch and display
    fetch_and_display_random_quote()

async def on_stop():
    """
    Code executed on stop. Make sure, everything is cleaned up nicely.

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    global screen, colors

    dprint("on stop")

    # Reset all states and clean up widgets
    colors = None
    screen = None
