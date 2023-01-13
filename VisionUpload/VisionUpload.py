from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import os
import time
import datetime
from tkinter import filedialog
from tkinter import *
import chromedriver_autoinstaller

chromedriver_autoinstaller.install()  # Check if the current version of chromedriver exists
                                      # and if it doesn't exist, download it automatically,
                                      # then add chromedriver to path

print(f"{'#'*80}\n{'#'*3}\n{'#'*3 + ' Vision Automatic Scan Upload Script'}\n{'#'*3}\n{'#'*80}\n")

DESKTOP = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop') 

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))

print(f"{'#'*3 + ' Select the folder containing the scan files to upload'}")
print(f"\nThe folder must be structured as:\n{' '*4}base folder (folder which you will select)\n{' '*4}|\n{' '*4}|\n{' '*4}{'-'*4}Deck 1 (must be spelled the same as in Vision)\n{' '*8}Deck 2\n{' '*8}|\n{' '*8}|\n{' '*8}{'-'*4}Date 1 (6 number date format i.e. 041122 for 4th November 2022)\n{' '*12}Date 2\n{' '*12}|\n{' '*12}|\n{' '*12}{'-'*4}Scan 001.e57\n{' '*16}Scan 002.e57\n")
print("### The module will be set to 'Module'\n")

root = Tk()
root.withdraw()
FILES_TO_UPLOAD_DIR = filedialog.askdirectory(title="Select folder containing scan files to upload")

if FILES_TO_UPLOAD_DIR == "":
    print("No folder selected! Exiting...")
    exit()

print("Uploading all files in", FILES_TO_UPLOAD_DIR, "\n")
total_size_bytes = 0
all_files_to_upload = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(FILES_TO_UPLOAD_DIR)) for f in fn]
for f in all_files_to_upload:
    stats = os.stat(os.path.join(FILES_TO_UPLOAD_DIR, f))
    # print(f, "-", stats.st_size/(1024**3), "GB")
    total_size_bytes += stats.st_size
print("\nFinal upload: ")
print("\t", "Total files:", len(all_files_to_upload))
print("\t", "Total size: ", total_size_bytes/(1024**3), "GB")
print("\t", "Estimated upload time:", (30*len(all_files_to_upload) + total_size_bytes/(1024**2)/100)/60/60, "hours @ 100 MBps")
print()

driver = webdriver.Chrome()


def drop_file(filePath, target, offsetX, offsetY):
    #if(!filePath.exists())
    #    throw new WebDriverException("File not found: " + filePath.toString());

    #driver = ((RemoteWebElement)target).getWrappedDriver()
    #wait = WebDriverWait(driver, 30)

    JS_DROP_FILE = \
        "var target = arguments[0]," + \
        "    offsetX = arguments[1]," + \
        "    offsetY = arguments[2]," + \
        "    document = target.ownerDocument || document," + \
        "    window = document.defaultView || window;" + \
        "" + \
        "var input = document.createElement('INPUT');" + \
        "input.type = 'file';" + \
        "input.style.display = 'none';" + \
        "input.onchange = function () {" + \
        "  var rect = target.getBoundingClientRect()," + \
        "      x = rect.left + (offsetX || (rect.width >> 1))," + \
        "      y = rect.top + (offsetY || (rect.height >> 1))," + \
        "      dataTransfer = { files: this.files };" + \
        "" + \
        "  ['dragenter', 'dragover', 'drop'].forEach(function (name) {" + \
        "    var evt = document.createEvent('MouseEvent');" + \
        "    evt.initMouseEvent(name, !0, !0, window, 0, 0, 0, x, y, !1, !1, !1, !1, 0, null);" + \
        "    evt.dataTransfer = dataTransfer;" + \
        "    target.dispatchEvent(evt);" + \
        "  });" + \
        "" + \
        "  setTimeout(function () { document.body.removeChild(input); }, 25);" + \
        "};" + \
        "document.body.appendChild(input);" + \
        "return input;"

    input =  driver.execute_script(JS_DROP_FILE, target, offsetX, offsetY);
    input.send_keys(filePath);
    #wait.until(ExpectedConditions.stalenessOf(input));



driver.get("http://gdi.vision")

CREATE_BUTTON_XPATH = "//span[contains(.,'Create')]"
CONTINUE_BUTTON_XPATH = "//span[contains(.,'Continue')]"
UPLOAD_AREA_XPATH = "//*[contains(text(),'Click here to Upload')]"
SAVE_BUTTON_XPATH = "//span[contains(.,'Save')]"
#SELECT_DROPDOWN_XPATH = "/html/body/div[1]/div[1]/div[7]/div/div[1]/div[2]/div/div/div[3]/div[1]/div/div[1]/div[1]/input[1]"

print(f"{'#'*80}\n{'#'*3}\n{'#'*3 + ' Log in to Vision and navigate to the scan upload page...'}\n{'#'*3 + ' Press return when you are ready to continue'}\n{'#'*3}\n{'#'*80}\n")

now = input("proceed?")



# MODULE_TEXT = input("What is the module: ")
MODULE_TEXT = "Module"

for level_dir in os.listdir(FILES_TO_UPLOAD_DIR):
    print(f"### Checking that {level_dir} exists")

    try:

        level_button = driver.find_element("xpath", f"//tr/td[contains(.,'{level_dir}')]")
        level_button.click()
        #print("Clicking CREATE")

        try:
            for date_dir in os.listdir(os.path.join(FILES_TO_UPLOAD_DIR, level_dir)):
                scan_date = datetime.datetime.strptime(date_dir, "%d%m%y").date()
        except:
            print(f"Invalid date format detected! Could not convert {os.path.join(level_dir/date_dir)} to a valid date! The date must be formatted as a 6 digit date ddmmyy! Exiting...")
            exit()
        time.sleep(3)

    except:

        print(f"Can't find {level_dir} button, Are you sure it is spelled the same as in Vision? Exiting...")
        exit()


for level_dir in os.listdir(FILES_TO_UPLOAD_DIR):
    print(f"{'#'*80}\n{'#'*3}\n{'#'*3 + ' Level: {level_dir}'}\n{'#'*3}\n{'#'*80}\n")

    level_button = driver.find_element("xpath", f"//tr/td[contains(.,'{level_dir}')]")
    level_button.click()

    for date_dir in os.listdir(os.path.join(FILES_TO_UPLOAD_DIR, level_dir)):
        scan_date = datetime.datetime.strptime(date_dir, "%d%m%y").date()
        date_string = scan_date.strftime("%d-%b-%Y")
        print("### Date:", date_string, "-", len(os.listdir(os.path.join(FILES_TO_UPLOAD_DIR, level_dir, date_dir))), "scan files", "\n")

        log_filename = os.path.join(FILES_TO_UPLOAD_DIR, level_dir, date_dir, "uploaded.log")
        try:
            with open(log_filename, "r") as log_file:
                uploaded_files = log_file.readlines()
        except:
            uploaded_files = []

        print("uploaded already", uploaded_files)

        for scan_file in os.listdir(os.path.join(FILES_TO_UPLOAD_DIR, level_dir, date_dir)):
            if scan_file == "uploaded.log":
                continue
            if scan_file in [f.strip() for f in uploaded_files]:
                print(f"{scan_file} has already been uploaded! skipping...")
                continue

            print("# Uploading", scan_file)

            try:

                current_date = datetime.datetime.now()
        
                create = driver.find_elements("xpath", CREATE_BUTTON_XPATH)[1]
                create.click()
                #print("Clicking CREATE")
                time.sleep(3)

                continue_ = driver.find_element("xpath", CONTINUE_BUTTON_XPATH)
                continue_.click()
                #("Clicking CONTINUE")
                time.sleep(2)

                date_input = driver.find_element("xpath", "//label[contains(.,'Date')]")
                date_input.click()
                time.sleep(2)
                
                month_year_top_button_string = current_date.strftime("%B %Y")
                #print("month_year_top_button_string", month_year_top_button_string )
                month_year_top_button = driver.find_element("xpath", f"//button[contains(.,'{month_year_top_button_string}')]")
                month_year_top_button.click()
                time.sleep(2)

                year_top_button_string = current_date.strftime("%Y")
                #print("year_top_button_string", year_top_button_string )
                year_top_button = driver.find_element("xpath", f"//button[contains(.,'{year_top_button_string}')]")
                year_top_button.click()
                time.sleep(2)

                year_button_string = scan_date.strftime("%Y")
                #print("year_button_string", year_button_string )
                year_button = driver.find_element("xpath", f"//li[contains(.,'{year_button_string}')]")
                year_button.click()
                time.sleep(2)

                month_button_string = scan_date.strftime("%b")
                #print("month_button_string", month_button_string )
                month_button = driver.find_element("xpath", f"//button/div[contains(.,'{month_button_string}')]")
                month_button.click()
                time.sleep(2)

                day_button_string = scan_date.strftime("%d")
                if day_button_string[0] == "0":
                    day_button_string = day_button_string[1]
                #print("day_button_string", day_button_string )
                day_button = driver.find_element("xpath", f"//button/div[contains(.,'{day_button_string}')]")
                day_button.click()
                #print("clicking date")
                time.sleep(2)

                dropdown = driver.find_element("xpath", "//*[@data-vv-name='Module']")
                dropdown.send_keys(MODULE_TEXT)
                #print("sending module text")
                time.sleep(2)
                dropdown.send_keys(Keys.RETURN)
                #print("sending return")
                time.sleep(2)

                drop_area = driver.find_element("xpath", "//*[contains(text(),'Click')]")
                #print("drop area:", drop_area)
        
                drop_file(os.path.join(FILES_TO_UPLOAD_DIR, level_dir, date_dir, scan_file), drop_area, 0, 0)
                #print("dropping file")
                time.sleep(2)

                while 1:
                    try:
                        driver.find_element("xpath", "//*[contains(text(),'Click')]")
                        break
                    except Exception as e:
                        #print("couldn't find element", e)
                        time.sleep(0.1)

                time.sleep(2)

                save = driver.find_element("xpath", SAVE_BUTTON_XPATH)
                save.click()
                print("Clicking Save")
                time.sleep(5)

                with open(log_filename, "a") as myfile:
                    myfile.write(scan_file + "\n")


            except Exception as e:
                print("error:", e)