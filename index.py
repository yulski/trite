from platform import system as system_name
import subprocess
import time
import datetime
import smtplib
import dropbox
import config

init_time = 0
init_datetime = ""
start_time = 0
report_template = "report.html"
host = "8.8.8.8"
failure_words = set(["host unreachable", "timed out", "failure"])
success_total = {"today": 0, "overall": 0}
failure_total = {"today": 0, "overall": 0}
is_down = False
went_down = 0
down_secs = {"today": 0, "overall": 0}

def is_ping_success(output):
    for word in failure_words:
        if word in output:
            return False
    return True

def ping():
    output = str(subprocess.Popen(["ping", host], stdout = subprocess.PIPE).communicate()[0])
    return is_ping_success(output)

def handle_success():
    global success_total
    global is_down
    global went_down
    global down_secs
    success_total["today"] += 1
    if is_down:
        is_down = False
        down_secs["today"] += (int(time.time()) - went_down)
        went_down = 0
    print("success")

def handle_failure():
    global failure_total
    global is_down
    global went_down
    failure_total["today"] += 1
    if not is_down:
        is_down = True
        went_down = int(time.time())
    print("failure")

def output_report():
    print("\n")
    print("---Report---")
    print("success total (today):", success_total["today"])
    print("failure total (today):", failure_total["today"])
    print("is down:", is_down)
    print("went down:", went_down)
    print("down secs (today):", down_secs["today"])
    print("\n")

def have_24_hours_passed():
    start_plus_24_h = start_time + (24 * 60 * 60)
    return int(time.time()) >= start_plus_24_h

def add_today_to_overall():
    success_total["overall"] += success_total["today"]
    failure_total["overall"] += failure_total["today"]
    down_secs["overall"] += down_secs["today"]

def reset():
    global start_time
    global success_total
    global failure_total
    global down_secs
    start_time = int(time.time())
    success_total["today"] = 0
    failure_total["today"] = 0
    down_secs["today"] = 0

def generate_html_report():
    pings_today = success_total["today"] + failure_total["today"]
    pings_overall = success_total["overall"] + failure_total["overall"]
    today_percentage = float(success_total["today"])*(100.0 / float(pings_today))
    overall_percentage = float(success_total["overall"])*(100.0/float(pings_overall))
    template_params = {"date": str(datetime.datetime.now()),
        "today_successes": success_total["today"],
        "overall_successes": success_total["overall"],
        "today_failures": failure_total["today"],
        "overall_failures": failure_total["overall"],
        "today_down_secs": down_secs["today"],
        "overall_down_secs": down_secs["overall"],
        "today_up_percentage": today_percentage,
        "overall_up_percentage": overall_percentage,
        "init_datetime": init_datetime}
    with open(report_template, "r") as template_file:
        template_str = template_file.read()
        return template_str % template_params

def send_report_email(report):
    email_from = "From: Trite app <" + config.email_addr + ">"
    email_to = "To: " + config.my_name + "<" + config.my_email + ">"
    message = email_from + "\n" + email_to + "\nMIME-Version: 1.0\nContent-Type: text/html\nSubject: Your daily Trite report\n" + report
    server = smtplib.SMTP(config.smtp_server, config.smtp_port)
    server.starttls()
    server.login(config.email_addr, config.email_pass)
    print("Sending report email...")
    server.sendmail(config.email_addr, config.my_email, message)
    server.quit()

def save_report_to_dropbox(report):
    dbx = dropbox.Dropbox(config.dropbox_access_token)
    contents = report.encode("utf-8")
    location = config.dropbox_save_location + "/" + str(datetime.datetime.now()) + ".html"
    print("Uploading report to Dropbox...")
    dbx.files_upload(contents, location)

def init():
    global start_time
    global init_time
    global init_datetime
    start_time = int(time.time())
    init_time = int(time.time())
    init_datetime = str(datetime.datetime.now())

def main():
    init()
    counter = 1
    while True:
        handle_success() if ping() else handle_failure()
        if counter % 5 == 0:
            output_report()
        # FIXME if internet is down on 24h interval, there will be no reset and today will overflow into the next day
        if have_24_hours_passed() and not is_down:
            add_today_to_overall()
            report = generate_html_report()
            send_report_email(report)
            save_report_to_dropbox(report)
            reset()
        counter = ((counter + 1) % 6) or 1
        time.sleep(5)

if __name__ == "__main__":
    main()
