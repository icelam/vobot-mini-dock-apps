import lvgl as lv
import clocktime
import utime
import ujson
import net
import urequests

# ---------- App Name ----------
NAME = "HK Public Holidays"

# ---------- Configuration ----------
CAN_BE_AUTO_SWITCHED: bool = True
DEBUG: bool = False
API_URL: str = "https://www.1823.gov.hk/common/ical/tc.json"

# ---------- App Icon ----------
ICON: str = "A:apps/public-holidays/resources/icon.png"

# ---------- Constants ----------
SCREEN_WIDTH: int = 320
SCREEN_HEIGHT: int = 240

# ---------- LVGL Widget ----------
font_chinese = lv.binfont_create("A:apps/public-holidays/fonts/NotoSansTC_20_bpp2.bin")

# List container
list_container = None

# ---------- State ----------
last_api_call_date = 0
holiday_count = 0
previous_focus_index = -1

# ---------- Styles ----------
def reset_style(style_object):
    style_object.set_bg_opa(lv.OPA.COVER)
    style_object.set_bg_color(lv.color_hex(0xFFFFFF))
    style_object.set_text_color(lv.color_hex(0x454545))
    style_object.set_border_width(0)
    style_object.set_pad_all(0)
    style_object.set_radius(0)
    style_object.set_width(SCREEN_WIDTH)
    style_object.set_text_font(font_chinese)

# Header style
header_style = lv.style_t()
header_style.init()
reset_style(header_style)
header_style.set_bg_color(lv.color_hex(0xFDCB6E))
header_style.set_text_color(lv.color_hex(0x454545))
header_style.set_pad_all(12)

# List style
list_style = lv.style_t()
list_style.init()
reset_style(list_style)

# Container style
container_style = lv.style_t()
container_style.init()
reset_style(container_style)
container_style.set_bg_opa(lv.OPA.TRANSP)

# Item style
item_style = lv.style_t()
item_style.init()
reset_style(item_style)
item_style.set_pad_ver(5)
item_style.set_pad_hor(10)
item_style.set_border_color(lv.color_hex(0xEEEEEE))
item_style.set_border_width(2)
item_style.set_border_side(lv.BORDER_SIDE.BOTTOM)

# Focused style
focused_item_style = lv.style_t()
focused_item_style.init()
focused_item_style.set_bg_color(lv.color_hex(0xf0f0f0))

# Chips style
chip_style = lv.style_t()
chip_style.init()
reset_style(chip_style)
chip_style.set_radius(5)
chip_style.set_pad_all(10)
chip_style.set_text_align(lv.TEXT_ALIGN.CENTER)
chip_style.set_bg_color(lv.color_hex(0x000000))
chip_style.set_text_color(lv.color_hex(0xffffff))

# Remarks style
remarks_style = lv.style_t()
remarks_style.init()
reset_style(remarks_style)
remarks_style.set_pad_ver(2)
remarks_style.set_bg_opa(lv.OPA.TRANSP)
remarks_style.set_text_color(lv.color_hex(0x999999))
remarks_style.set_text_font(lv.font_ascii_14)

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

        response = urequests.get(url, headers={"Content-Type": "application/json"})

        if response.status_code == 200:
            dprint(f"Got response with status code {response.status_code}")
            # API response from 1823.gov.hk returns BOM character at the beginning of file
            # which we have to remove it to parse the JSON properly
            return ujson.loads(response.text[1:] if response.text.startswith('\ufeff') else response.text)
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
    global holiday_count
    e_code = event.get_code()

    # dprint(f"Got code {e_code}")

    if holiday_count > 0 and e_code == lv.EVENT.KEY:
        e_key = event.get_key()
        dprint(f"Got key {e_key}")

        if e_key == lv.KEY.LEFT:
            focus_item((previous_focus_index + 1) % holiday_count)
        elif e_key == lv.KEY.RIGHT:
            focus_item((previous_focus_index - 1) % holiday_count)

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

def get_current_date() -> int:
    """
    Get and return current date as YYYYMMDD format

    Returns:
        int: Current date in YYYYMMDD format.
    """
    current_time = clocktime.datetime()
    year = current_time[0]
    month = current_time[1]
    day = current_time[2]

    formatted_date = '{:04d}{:02d}{:02d}'.format(year, month, day)
    return int(formatted_date)

def days_between(date1: int, date2: int):
    time_info = (0, 0, 0, 0, 0)
    datetime1 = (date1 // 10000, date1 % 10000 // 100, date1 % 100) + time_info
    datetime2 = (date2 // 10000, date2 % 10000 // 100, date2 % 100) + time_info
    return abs(utime.mktime(datetime1) // (24 * 3600) - utime.mktime(datetime2) // (24 * 3600))

def fetch_and_display_public_holiday(current_date: int) -> None:
    """
    Display future public holiday on screen

    Returns:
        None. The main screen is displayed on the screen with updated public holidays.
    """
    global list_container, holiday_count
    dprint("Update screen")

    main_scr = lv.obj()

    # Add header
    header = lv.label(main_scr)
    header.set_text("香港公眾假期")
    header.align(lv.ALIGN.TOP_LEFT, 0, 0)
    header.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
    header.add_style(header_style, 0)
    header.update_layout()

    container_height = SCREEN_HEIGHT - header.get_height();

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
    future_events = [event for event in response['vcalendar'][0]['vevent'] if int(event['dtstart'][0]) >= current_date]

    for event in future_events:
        item = lv.obj(list_container)
        item.add_style(item_style, 0)
        item.add_style(focused_item_style, lv.STATE.FOCUSED)
        item.set_size(SCREEN_WIDTH, container_height // 3)

        left_content = lv.obj(item)
        left_content.add_style(container_style, 0)
        left_content.align(lv.ALIGN.LEFT_MID, 0, 0)
        left_content.set_size(140, (container_height // 3) - 12);

        name_label = lv.label(left_content)
        name_label.set_text(event['summary'])
        name_label.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
        name_label.set_style_pad_ver(5, 0)
        name_label.set_width(140)
        name_label.align(lv.ALIGN.TOP_LEFT, 0, 0)

        date_label = lv.label(left_content)
        date_label.add_style(remarks_style, 0)
        date_str = event['dtstart'][0]
        date_label.set_text(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}")
        date_label.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
        date_label.set_width(140)
        date_label.align(lv.ALIGN.BOTTOM_LEFT, 0, 0)

        countdown_chip = lv.label(item)
        countdown_chip.add_style(chip_style, 0)
        holiday_date = int(event['dtstart'][0])
        countdown = days_between(current_date, holiday_date)
        countdown_chip.set_text(f"還有 {countdown} 天" if countdown > 0 else "今天")
        countdown_chip.set_style_bg_color(lv.color_hex(0x4C89B2) if countdown > 0 else lv.color_hex(0xE25E55), 0)
        countdown_chip.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
        countdown_chip.set_width(140)
        countdown_chip.align(lv.ALIGN.RIGHT_MID, 0, 0)

        holiday_count = len(future_events)

    lv.screen_load(main_scr)

# ---------- Lifecycle hooks ----------
async def on_start():
    """
    Code executed on start.

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    global last_api_call_date
    dprint('on start')

    display_loading_screen("Loading...")

    # Initial fetch and display
    try:
        current_date = get_current_date()
        last_api_call_date = current_date
        fetch_and_display_public_holiday(current_date)
    except Exception as e:
        display_error_screen(f"Error occured on start: {e}")

async def on_running_foreground():
    """
    Code executed once the App becomes active, called by system approx. every 200ms

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    global last_api_call_date
    current_date: int = get_current_date()

    try:
        # Re-fetch latest data according to fetch interval settings
        if current_date != last_api_call_date:
            last_api_call_date = current_date
            fetch_and_display_public_holiday(current_date)
    except Exception as e:
        display_error_screen(f"Error occured on running foreground: {e}")

async def on_stop():
    """
    Code executed on stop. Make sure, everything is cleaned up nicely.

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    global list_container, last_api_call_date, holiday_count, previous_focus_index
    dprint('on stop')

    list_container = None

    # Reset states since they seems to be preserved when pressing back (ESC) button
    last_api_call_date = 0
    holiday_count = 0
    previous_focus_index = -1
