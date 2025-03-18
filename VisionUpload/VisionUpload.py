#!/usr/bin/env python3
"""
Vision Automatic Scan Upload Script
"""

import os
import time
import datetime
import logging
from tkinter import filedialog, Tk

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

# ------------------------- Configuration & Constants -------------------------

DEBUG_MODE = False  # Set to True during development to enable debug pauses

# Setup logging: if debug mode is enabled, use DEBUG; otherwise use INFO.
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Centralized selectors and constants.
SELECTORS = {
    "create_button": "//button[contains(@class, 'v-btn') and .//span[normalize-space()='Create']]",
    "continue_button": "//button[contains(@class, 'v-btn') and .//span[normalize-space()='Continue']]",
    "save_button": "//button[contains(@class, 'v-btn') and .//span[normalize-space()='Save']]",
    "date_label": "//label[normalize-space(.)='Date *']/following-sibling::input",
    "module_dropdown": "//*[@data-vv-name and normalize-space(@data-vv-name)='Module']",
    "survey_dropdown": "//*[@data-vv-name and normalize-space(@data-vv-name)='Survey']",
    "upload_area": "//div[contains(concat(' ', normalize-space(@class), ' '), ' drop ')]",
}

MODULE_TEXT = "Module"
VISION_URL = "http://gdi.vision"
UPLOADED_LOG_FILENAME = "uploaded.log"

# ------------------------- Helper Functions -------------------------


def debug_pause(message="DEBUG MODE: Press Enter to continue..."):
    """Pauses execution if DEBUG_MODE is True."""
    if DEBUG_MODE:
        input(message)


def wait_for_element(driver, by, value, timeout=10):
    """Waits for an element to be present and returns it."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def wait_for_clickable(driver, by, value, timeout=10):
    """Waits for an element to be clickable and returns it."""
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))


def drop_file(driver, file_path, target, offsetX=0, offsetY=0):
    """
    Simulates drag-and-drop file upload by injecting a hidden file input.
    """
    JS_DROP_FILE = (
        "var target = arguments[0],"
        "    offsetX = arguments[1],"
        "    offsetY = arguments[2],"
        "    document = target.ownerDocument || document,"
        "    window = document.defaultView || window;"
        "var input = document.createElement('INPUT');"
        "input.type = 'file';"
        "input.style.display = 'none';"
        "input.onchange = function () {"
        "  var rect = target.getBoundingClientRect(),"
        "      x = rect.left + (offsetX || (rect.width >> 1)),"
        "      y = rect.top + (offsetY || (rect.height >> 1)),"
        "      dataTransfer = { files: this.files };"
        "  ['dragenter', 'dragover', 'drop'].forEach(function (name) {"
        "    var evt = document.createEvent('MouseEvent');"
        "    evt.initMouseEvent(name, true, true, window, 0, 0, 0, x, y, false, false, false, false, 0, null);"
        "    evt.dataTransfer = dataTransfer;"
        "    target.dispatchEvent(evt);"
        "  });"
        "  setTimeout(function () { document.body.removeChild(input); }, 25);"
        "};"
        "document.body.appendChild(input);"
        "return input;"
    )
    try:
        input_element = driver.execute_script(JS_DROP_FILE, target, offsetX, offsetY)
        input_element.send_keys(file_path)
    except WebDriverException as e:
        logging.error("Error dropping file: %s", e)
        raise


def login_to_vision(driver, url):
    """
    Navigates to the Vision login page and waits for the user to log in manually.
    """
    driver.get(url)
    logging.info("Navigated to %s", url)
    input("Log in to Vision and then press Enter to continue...")  # Manual login step


def navigate_to_level(driver, level_dir):
    """
    Attempts to locate and click on a level button (i.e. Deck) on the Vision page.
    """
    try:
        level_button = wait_for_clickable(
            driver, By.XPATH, f"//tr/td[contains(.,'{level_dir}')]"
        )
        level_button.click()
        logging.info("Clicked on level '%s'", level_dir)
    except TimeoutException:
        logging.error("Level '%s' not found on the page.", level_dir)
        raise


def select_date(driver, scan_date, current_date):
    """
    Selects the scan date by interacting with the date-picker.
    The method assumes the date-picker uses buttons with text containing month/year/day.
    """
    try:
        # Click on the date input field
        date_input = wait_for_clickable(driver, By.XPATH, SELECTORS["date_label"])
        driver.execute_script("arguments[0].click();", date_input)
        logging.debug("Clicked on date input")

        # Select the month/year header
        month_year_top = wait_for_clickable(
            driver,
            By.XPATH,
            "//div[contains(@class, 'v-date-picker-header__value')]//button",
        )
        month_year_top.click()
        logging.debug("Clicked on month/year header")

        # Wait for the year selector to appear
        time.sleep(1.5)

        # Click the year header (again using the same selector as above)
        year_top = wait_for_clickable(
            driver,
            By.XPATH,
            "//div[contains(@class, 'v-date-picker-header__value')]//button",
        )
        year_top.click()
        logging.debug("Clicked on year header")

        # Select the specific year for the scan date
        year_str = scan_date.strftime("%Y")
        year_button = wait_for_clickable(
            driver, By.XPATH, f"//li[contains(.,'{year_str}')]"
        )
        year_button.click()
        logging.debug("Selected scan year: %s", year_str)

        # Select the desired month
        month_str = scan_date.strftime("%b")
        month_button = wait_for_clickable(
            driver, By.XPATH, f"//button/div[contains(.,'{month_str}')]"
        )
        month_button.click()
        logging.debug("Selected scan month: %s", month_str)

        # Select the desired day (removing any leading zero)
        day_str = scan_date.strftime("%d").lstrip("0")
        day_button = wait_for_clickable(
            driver, By.XPATH, f"//button/div[contains(.,'{day_str}')]"
        )
        day_button.click()
        logging.debug("Selected scan day: %s", day_str)

    except TimeoutException as e:
        logging.error("Timeout while selecting date: %s", e)
        raise


def select_module(driver, module_text):
    """
    Finds the module dropdown, sends the module text, and confirms the selection.
    """
    try:
        dropdown = wait_for_clickable(driver, By.XPATH, SELECTORS["module_dropdown"])
        dropdown.clear()
        dropdown.send_keys(module_text)
        logging.debug("Entered module text: %s", module_text)
        dropdown.send_keys(Keys.RETURN)
        logging.debug("Confirmed module selection")
    except TimeoutException:
        logging.error("Module dropdown not found.")
        raise


def select_survey(driver, survey_text):
    """
    Finds the survey dropdown, sends the survey text, and confirms the selection.
    """
    try:
        dropdown = wait_for_clickable(driver, By.XPATH, SELECTORS["survey_dropdown"])
        dropdown.clear()
        dropdown.send_keys(survey_text)
        logging.debug("Entered survey text: %s", survey_text)
        dropdown.send_keys(Keys.RETURN)
        logging.debug("Confirmed survey selection")
    except TimeoutException:
        logging.error("Survey dropdown not found.")
        raise


def upload_scan_file(driver, file_path, scan_date, module_text, survey_text):
    """
    Executes the full sequence to upload a single scan file.
    """
    current_date = datetime.datetime.now()

    # Click the "Create" button (using the 3rd instance of the element, per original script)
    try:
        create_buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, SELECTORS["create_button"]))
        )
        if len(create_buttons) < 3:
            raise Exception("Not enough 'Create' buttons found.")
        create_button = create_buttons[2]
        wait_for_element(driver, By.XPATH, SELECTORS["create_button"])
        create_button.click()
        logging.info("Clicked Create button")
    except TimeoutException as e:
        logging.error("Create button not clickable: %s", e)
        raise

    # Click the "Continue" button
    try:
        continue_button = wait_for_clickable(
            driver, By.XPATH, SELECTORS["continue_button"]
        )
        continue_button.click()
        logging.info("Clicked Continue button")
    except TimeoutException:
        logging.error("Continue button not clickable.")
        raise

    # Set the scan date using the date picker
    select_date(driver, scan_date, current_date)

    # Set the module field
    select_module(driver, module_text)

    # Set the survey field
    select_survey(driver, survey_text)

    # Locate the drop area (by class name) and drop the file
    try:
        drop_area = wait_for_clickable(driver, By.CLASS_NAME, "drop")
        drop_file(driver, file_path, drop_area)
        logging.info("Dropped file: %s", file_path)
    except Exception as e:
        logging.error("Error during file drop: %s", e)
        raise

    # Wait until the upload completes (i.e. "Uploading" text is gone)
    try:
        WebDriverWait(driver, 300).until_not(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(text(),'Uploading')]")
            )
        )
        logging.info("File upload completed for %s", file_path)
    except TimeoutException:
        logging.warning("Upload may be taking too long for file %s", file_path)

    # Click the "Save" button
    try:
        save_button = wait_for_clickable(driver, By.XPATH, SELECTORS["save_button"])
        save_button.click()
        logging.info("Clicked Save button for %s", file_path)
    except TimeoutException:
        logging.error("Save button not clickable for %s", file_path)
        raise


def retry_action(action, retries=3, delay=2):
    """
    Tries to perform an action up to 'retries' times before failing.
    """
    for attempt in range(retries):
        try:
            return action()
        except Exception as e:
            logging.warning("Attempt %d failed: %s", attempt + 1, e)
            time.sleep(delay)
    raise Exception("Action failed after {} retries.".format(retries))


# ------------------------- New Helper Functions for Folder Summary & Validation -------------------------


def print_directory_tree(startpath):
    """
    Prints a tree-view of the directory structure starting at startpath,
    excluding any log files.
    """
    print("\nFolder Structure Summary:")
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, "").count(os.sep)
        indent = " " * 4 * level
        folder_name = os.path.basename(root) if os.path.basename(root) else startpath
        print(f"{indent}{folder_name}/")
        subindent = " " * 4 * (level + 1)
        for f in files:
            if f == UPLOADED_LOG_FILENAME:
                continue  # Skip printing log files
            print(f"{subindent}{f}")
    print()  # Extra newline at the end


def validate_folder_structure(parent_folder):
    """
    Validates that the folder structure matches the expected layout:
      Parent Folder
          └── Survey Folder(s)
                   └── Level Folder(s)
                             └── Date Folder(s) (name in ddmmyy format)
                                        └── Scan files (excluding log files)
    Returns True if valid; otherwise False.
    """
    valid = True
    survey_dirs = [
        d
        for d in os.listdir(parent_folder)
        if os.path.isdir(os.path.join(parent_folder, d))
    ]
    if not survey_dirs:
        logging.error("No survey directories found in the parent folder.")
        valid = False

    for survey in survey_dirs:
        survey_path = os.path.join(parent_folder, survey)
        level_dirs = [
            d
            for d in os.listdir(survey_path)
            if os.path.isdir(os.path.join(survey_path, d))
        ]
        if not level_dirs:
            logging.error("Survey '%s' does not contain any level directories.", survey)
            valid = False
        else:
            for level in level_dirs:
                level_path = os.path.join(survey_path, level)
                date_dirs = [
                    d
                    for d in os.listdir(level_path)
                    if os.path.isdir(os.path.join(level_path, d))
                ]
                if not date_dirs:
                    logging.error(
                        "Level '%s' in survey '%s' does not contain any date directories.",
                        level,
                        survey,
                    )
                    valid = False
                else:
                    for date_dir in date_dirs:
                        # Check for correct date format (ddmmyy)
                        try:
                            _ = datetime.datetime.strptime(date_dir, "%d%m%y").date()
                        except ValueError:
                            logging.error(
                                "Directory '%s' in level '%s' of survey '%s' is not in ddmmyy format.",
                                date_dir,
                                level,
                                survey,
                            )
                            valid = False
                            continue
                        date_path = os.path.join(level_path, date_dir)
                        # Exclude the uploaded log file from scan files
                        scan_files = [
                            f
                            for f in os.listdir(date_path)
                            if os.path.isfile(os.path.join(date_path, f))
                            and f != UPLOADED_LOG_FILENAME
                        ]
                        if not scan_files:
                            logging.error(
                                "Date directory '%s' in level '%s' of survey '%s' does not contain any scan files.",
                                date_dir,
                                level,
                                survey,
                            )
                            valid = False
    return valid


# ------------------------- Main Process -------------------------


def main():
    # Display introductory information in the log.
    logging.info("#" * 80)
    logging.info("### Vision Automatic Scan Upload Script")
    logging.info("#" * 80)
    logging.info(
        "IMPORTANT: Please select the **parent folder** that contains your survey data."
    )
    logging.info("The folder structure must follow the template below:")
    logging.info("Parent Folder (the folder you select)")
    logging.info(
        "└── Survey Folder (e.g. 'Blanket Scan' - must match the name in Vision)"
    )
    logging.info(
        "    └── Level Folder (e.g. 'Level 1' — must match the name in Vision)"
    )
    logging.info("        └── Date Folder (format: ddmmyy, e.g., '041122')")
    logging.info("            └── Scan files (e.g., 'Scan 001.e57', 'Scan 002.e57')")
    logging.info("The module will be set to '%s'", MODULE_TEXT)

    # Choose the parent folder containing survey folders using a Tkinter dialog.
    root = Tk()
    root.withdraw()
    files_to_upload_dir = filedialog.askdirectory(
        title="Select parent folder containing survey folders to upload"
    )
    if not files_to_upload_dir:
        logging.error("No folder selected! Exiting...")
        return

    logging.info("Parent folder selected: %s", files_to_upload_dir)

    # Print a summary of the directory structure.
    print_directory_tree(files_to_upload_dir)

    # Validate the folder structure.
    if not validate_folder_structure(files_to_upload_dir):
        logging.error("The folder structure does not match the expected layout.")
        proceed = input(
            "The folder structure appears invalid. Do you want to continue with the upload? (y/n): "
        )
        if proceed.lower() != "y":
            logging.info("Exiting per user request.")
            return
    else:
        logging.info("Folder structure appears valid.")

    # Calculate total size and count of files for informational purposes.
    total_size_bytes = 0
    all_files = []
    for dp, dn, filenames in os.walk(files_to_upload_dir):
        for f in filenames:
            file_full_path = os.path.join(dp, f)
            all_files.append(file_full_path)
            total_size_bytes += os.path.getsize(file_full_path)
    logging.info(
        "Final upload: Total files: %d, Total size: %.2f GB",
        len(all_files),
        total_size_bytes / (1024**3),
    )
    estimated_time = (30 * len(all_files) + total_size_bytes / (1024**2) / 100) / 3600
    logging.info("Estimated upload time: %.2f hours @ 100 MBps", estimated_time)

    # Initialize the Selenium Chrome driver.
    driver = webdriver.Chrome()
    driver.maximize_window()

    # Log in to Vision (manual step).
    login_to_vision(driver, VISION_URL)

    # Iterate through each survey folder in the parent folder.
    for survey_dir in os.listdir(files_to_upload_dir):
        survey_path = os.path.join(files_to_upload_dir, survey_dir)
        if not os.path.isdir(survey_path):
            continue

        # The survey name is taken from the survey folder's basename.
        survey_name = survey_dir
        logging.info("Processing Survey: %s", survey_name)

        # Loop over each level (Deck) directory inside the current survey folder.
        for level_dir in os.listdir(survey_path):
            level_path = os.path.join(survey_path, level_dir)
            if not os.path.isdir(level_path):
                continue

            logging.info("Checking that level '%s' exists in Vision", level_dir)
            try:
                navigate_to_level(driver, level_dir)
            except Exception as e:
                logging.error("Skipping level '%s' due to error: %s", level_dir, e)
                continue

            # Loop over each date directory within the current level.
            for date_dir in os.listdir(level_path):
                date_path = os.path.join(level_path, date_dir)
                if not os.path.isdir(date_path):
                    continue
                try:
                    scan_date = datetime.datetime.strptime(date_dir, "%d%m%y").date()
                except ValueError:
                    logging.error(
                        "Invalid date format for directory '%s'. Must be ddmmyy. Skipping...",
                        date_dir,
                    )
                    continue

                date_string = scan_date.strftime("%d-%b-%Y")
                logging.info("Processing Level: '%s', Date: %s", level_dir, date_string)

                # Load (or initialize) a log file to track already uploaded files.
                log_filename = os.path.join(date_path, UPLOADED_LOG_FILENAME)
                try:
                    with open(log_filename, "r") as log_file:
                        uploaded_files = [line.strip() for line in log_file.readlines()]
                except IOError:
                    uploaded_files = []

                # Loop over each scan file in the date directory.
                for scan_file in os.listdir(date_path):
                    if scan_file == UPLOADED_LOG_FILENAME:
                        continue
                    if scan_file in uploaded_files:
                        logging.info(
                            "File '%s' already uploaded. Skipping...", scan_file
                        )
                        continue

                    file_path = os.path.join(date_path, scan_file)
                    logging.info("Uploading file: %s", file_path)

                    try:
                        # Use retry_action to handle intermittent issues.
                        retry_action(
                            lambda: upload_scan_file(
                                driver, file_path, scan_date, MODULE_TEXT, survey_name
                            ),
                            retries=3,
                            delay=2,
                        )
                        # Log the successful upload.
                        with open(log_filename, "a") as log_file:
                            log_file.write(scan_file + "\n")
                    except Exception as e:
                        logging.error("Error uploading file '%s': %s", scan_file, e)
                        continue

                    # Optional pause for manual inspection (only when debug mode is on)
                    debug_pause(
                        "File uploaded. Press Enter to continue with the next file..."
                    )

    logging.info("Upload process complete.")
    driver.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("An unexpected error occurred: %s", exc)
