import lvgl as lv
import clocktime
import json
import net
import urequests

# ---------- App Name ----------
NAME = "A&E Waiting Time"

# ---------- Configuration ----------
CAN_BE_AUTO_SWITCHED: bool = True
DEBUG: bool = False
API_URL: str = "https://www.ha.org.hk/opendata/aed/aedwtdata-tc.json"
FETCH_INTERVAL_IN_SECONDS: int = 300

# ---------- App Icon ----------
ICON: str = "A:apps/ha-ae-waiting-time/resources/icon.png"

# ---------- Constants ----------
SCREEN_WIDTH: int = 320
SCREEN_HEIGHT: int = 240

# ---------- LVGL Widget ----------
font_chinese = lv.binfont_create("A:apps/ha-ae-waiting-time/fonts/NotoSansTC_20_bpp2.bin")

# Main screen
main_scr = None
list_container = None
time_label_map = None

# ---------- State ----------
last_api_call_time = 0
hospital_count = 0
previous_focus_index = -1

# ---------- Styles ----------
def reset_style(style_object):
    style_object.set_bg_opa(lv.OPA.COVER)
    style_object.set_bg_color(lv.color_hex(0xFFFFFF))
    style_object.set_text_color(lv.color_hex(0x000000))
    style_object.set_border_width(0)
    style_object.set_pad_all(0)
    style_object.set_radius(0)
    style_object.set_width(SCREEN_WIDTH)
    style_object.set_text_font(font_chinese)

# Header style
header_style = lv.style_t()
header_style.init()
reset_style(header_style)
header_style.set_bg_color(lv.color_hex(0xFE0000))
header_style.set_text_color(lv.color_hex(0xFFFFFF))
header_style.set_pad_all(12)

# List style
list_style = lv.style_t()
list_style.init()
reset_style(list_style)

# item style
item_style = lv.style_t()
item_style.init()
reset_style(item_style)
item_style.set_pad_all(10)
item_style.set_border_color(lv.color_hex(0xEEEEEE))
item_style.set_border_width(2)
item_style.set_border_side(lv.BORDER_SIDE.BOTTOM)

# Focused style
focused_item_style = lv.style_t()
focused_item_style.init()
focused_item_style.set_bg_color(lv.color_hex(0xf0f0f0))

# ---------- Functions ----------
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
        response = urequests.get(url)

        if response.status_code == 200:
            dprint(f"Got response with status code {response.status_code}")
            return json.loads(response.text)
        else:
            raise Exception(f"Failed to load {url}, status code: {response.status_code}, response body: {response.text}")
    else:
        raise Exception(f"Wifi is not connected")

def display_fullscreen_message(message: str, is_error: bool = False) -> None:
    """
    Display fullscreen screen

    Args:
        message (str): Message to display on screen
        is_errror (bool): Indicates if the message is an error message that should be displayed in red

    Returns:
        None. The message is displayed on the screen.
    """
    error_scr = lv.obj()
    error_scr.set_style_bg_color(lv.color_hex(0x000000),0)

    message_label = lv.label(error_scr)
    message_label.center()
    message_label.set_long_mode(lv.label.LONG.WRAP)
    message_label.set_width(300)
    message_label.set_style_text_color(lv.color_hex(0xFF0000) if is_error else lv.color_hex(0xFFFFFF), 0)

    message_label.set_text(message)
    lv.screen_load(error_scr)

def display_error_screen(message: str) -> None:
    """
    Display error screen

    Args:
        message (str): Error message to display on screen

    Returns:
        None. The error screen is displayed on the screen.
    """
    display_fullscreen_message(message, True)

def display_loading_screen(message: str) -> None:
    """
    Display loading screen

    Args:
        message (str): loading message to display on screen

    Returns:
        None. The error screen is displayed on the screen.
    """
    display_fullscreen_message(message, False)

def event_handler(event) -> None:
    """
    Code executed when an event is called.

    Note:
    - This can be some paint events as well. Therefore, check the event code!
    - Don't call a method using "await"! Otherwise, the whole function becomes async!

    See https://docs.lvgl.io/master/overview/event.html for possible events.
    """
    global hospital_count
    e_code = event.get_code()

    # dprint(f"Got code {e_code}")

    if hospital_count > 0 and e_code == lv.EVENT.KEY:
        e_key = event.get_key()
        dprint(f"Got key {e_key}")

        if e_key == lv.KEY.LEFT:
            focus_item((previous_focus_index + 1) % hospital_count)
        elif e_key == lv.KEY.RIGHT:
            focus_item((previous_focus_index - 1) % hospital_count)

def focus_item(index: int) -> None:
    """
    Focus list item of given index

    Args:
        index (int): The index of the list item to focus

    Returns:
        None. The list item is focused.
    """
    global list_container, previous_focus_index
    current_item = list_container.get_child(index)

    if previous_focus_index != -1:
        previous_item = list_container.get_child(previous_focus_index)
        if previous_item:
            previous_item.remove_state(lv.STATE.FOCUSED)

    if current_item:
        current_item.add_state(lv.STATE.FOCUSED)
        current_item.scroll_to_view(lv.ANIM.OFF)

    previous_focus_index = index

def fetch_and_display_wait_time() -> None:
    """
    Display latest waiting time on screen

    Returns:
        None. The main screen is displayed on the screen with updated waiting time.
    """
    global main_scr, list_container, time_label_map, hospital_count
    dprint("Update screen")

    if not main_scr:
        main_scr = lv.obj()

        # Add header
        header = lv.label(main_scr)
        header.set_text("急症室等候時間")
        header.align(lv.ALIGN.TOP_LEFT, 0, 0)
        header.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        header.add_style(header_style, 0)
        header.update_layout()

        container_height = SCREEN_HEIGHT - header.get_height();
        print(container_height)

        # Add list container
        list_container = lv.list(main_scr)
        list_container.set_size(SCREEN_WIDTH, container_height)
        list_container.align(lv.ALIGN.TOP_LEFT, 0, header.get_height())
        list_container.set_scrollbar_mode(lv.SCROLLBAR_MODE.AUTO)
        list_container.add_style(list_style, 0)

        # Bind input events
        main_scr.add_event(event_handler, lv.EVENT.ALL, None)
        lv.group_get_default().add_obj(main_scr)
        lv.group_focus_obj(main_scr)
        lv.group_get_default().set_editing(True)

    response = request(API_URL)

    if not time_label_map:
        time_label_map = {}

        for wait_info in response["waitTime"]:
            item = lv.obj(list_container)
            item.add_style(item_style, 0)
            item.add_style(focused_item_style, lv.STATE.FOCUSED)
            item.set_height(50)

            name_label = lv.label(item)
            name_label.set_text(wait_info['hospName'])
            name_label.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
            name_label.set_width(150)
            name_label.align(lv.ALIGN.LEFT_MID, 0, 0)

            time_label = lv.label(item)
            time_label.set_text(wait_info['topWait'])
            time_label.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
            time_label.set_width(110)
            time_label.align(lv.ALIGN.RIGHT_MID, 0, 0)
            time_label.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)

            time_label_map[wait_info['hospName']] = time_label
            hospital_count = hospital_count + 1
    else:
        for wait_info in response["waitTime"]:
            time_label_map[wait_info['hospName']].set_text(wait_info['topWait'])

    lv.screen_load(main_scr)

# ---------- Lifecycle hooks ----------
async def on_start():
    """
    Code executed on start.

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    global last_api_call_time
    dprint('on start')

    display_loading_screen("Loading...")

    # Initial fetch and display
    try:
        last_api_call_time = clocktime.now()
        fetch_and_display_wait_time()
    except Exception as e:
        display_error_screen(f"Error occured on start: {e}")

async def on_running_foreground():
    """
    Code executed once the App becomes active, called by system approx. every 200ms

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    global last_api_call_time
    current_time: int = clocktime.now()

    try:
        # Re-fetch latest data according to fetch interval settings
        if current_time - last_api_call_time >= FETCH_INTERVAL_IN_SECONDS or current_time - last_api_call_time < 0:
            last_api_call_time = clocktime.now()
            fetch_and_display_wait_time()
    except Exception as e:
        display_error_screen(f"Error occured on running foreground: {e}")

async def on_stop():
    """
    Code executed on stop. Make sure, everything is cleaned up nicely.

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    global main_scr, time_label_map, list_container, last_api_call_time, hospital_count, previous_focus_index
    dprint('on stop')

    if main_scr:
        main_scr.clean()
        main_scr.del_async()
        main_scr = None

    # Reset states since they seems to be preserved when pressing back (ESC) button
    list_container = None
    time_label_map = None
    last_api_call_time = 0
    hospital_count = 0
    previous_focus_index = -1
