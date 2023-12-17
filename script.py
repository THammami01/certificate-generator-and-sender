import argparse
import csv
import json
import shutil
import smtplib
import uuid
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class ActionSelectionError(Exception):
    pass


class FileFormatError(Exception):
    pass


def get_attendees():
    """
    Retrieves the list of attendees from the 'attendees.csv' file.

    Returns:
        list[dict[str, str]]: A list of dictionaries containing the attendees' information.
            Each dictionary has keys 'fullname' and 'email' representing the attendee's full name and email address.
    """

    attendees: list[dict[str, str]] = []

    with open(".\\attendees.csv", encoding="utf-8") as csv_file:
        for row in csv.reader(csv_file, delimiter=","):
            attendees.append({"fullname": row[0], "email": row[1]})

    return attendees


def process_email_body(attendee: dict[str, str], body: str):
    """
    Replaces all keywords (starting with $) in the email body with equivalent attendee's data.

    Args:
        attendee (dict[str, str]): Attendee's email and full name.
        body (str): Body of the email before processing.

    Returns:
        str: Processed body of the email.
    """

    for key, val in attendee.items():
        body = body.replace(f"${key}", val)

    return body


def resize_cv2_image_with_aspect_ratio(
    image, width=None, height=None, inter=cv2.INTER_AREA
):
    """
    Resizes a cv2 image while maintaining its aspect ratio.

    Args:
        image (cv2 image): Image to be resized.
        width (int, optional): Desired width of the image.
        height (int, optional): Desired height of the image.
        inter (cv2 interpolation, optional): Interpolation method to be used.

    Returns:
        cv2 image: Resized image.
    """

    dim = None
    (h, w) = image.shape[:2]

    if width is None and height is None:
        return image
    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))

    return cv2.resize(image, dim, interpolation=inter)


def generate_certificate(attendee_idx: int, attendee: dict[str, str]):
    """
    Generates a certificate.

    Args:
        attendee_idx (int): The ID of the attendee.
        attendee (dict[str, str]): Attendee's email and full name.
    """

    image = cv2.imread(f".\\templates\\{data['template']['filename']}")
    image_width = image.shape[1]
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(image)
    draw = ImageDraw.Draw(image)

    if data["template"]["styles"].get("font-filename"):
        image_font = ImageFont.truetype(
            f".\\fonts\\{data['template']['styles']['font-filename']}",
            data["template"]["styles"]["size"],
        )
    else:
        image_font = ImageFont.load_default(data["template"]["styles"]["size"])

    w = draw.textlength(attendee["fullname"], image_font)
    left_coordinate = (image.width - w) / 2  # IN ORDER TO CENTER THE TEXT

    draw.text(
        (left_coordinate, data["template"]["styles"]["top-coordinate"]),
        attendee["fullname"],
        font=image_font,
        fill=data["template"]["styles"]["fill-color"],
    )

    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    if "preview" in actions:
        MAX_CV2_IMAGE_WIDTH = 900

        if image_width > MAX_CV2_IMAGE_WIDTH:
            resized_image = resize_cv2_image_with_aspect_ratio(
                image, width=MAX_CV2_IMAGE_WIDTH  # OR RESIZE BY HEIGHT: height=...
            )
            cv2.imshow(data["email"]["attached-certificate-filename"], resized_image)
        else:
            cv2.imshow(data["email"]["attached-certificate-filename"], image)

        cv2.waitKey()

    if "save" in actions or "send" in actions:
        Path(f".\\output\\{run_id}").mkdir(parents=True, exist_ok=True)
        cv2.imwrite(f".\\output\\{run_id}\\{attendee_idx}.{template_filetype}", image)

    print(f"CERTIFICATE {attendee_idx} GENERATED")


def send_certificate(attendee_idx: int, attendee: dict[str, str]):
    """
    Sends a certificate by email.

    Args:
        attendee_idx (int): The ID of the attendee.
        attendee (dict[str, str]): Attendee's email and full name.
    """

    msg = MIMEMultipart()
    msg["Subject"] = data["email"]["subject"]
    msg["From"] = data["email"]["sender-credentials"]["email"]
    msg["To"] = attendee["email"]

    msg.attach(MIMEText(process_email_body(attendee, data["email"]["body"]), "html"))

    with open(f".\\output\\{run_id}\\{attendee_idx}.{template_filetype}", "rb") as fp:
        img = MIMEImage(fp.read())
        img.add_header(
            "Content-Disposition",
            "attachment",
            filename=data["email"]["attached-certificate-filename"],
        )
        msg.attach(img)

    try:
        # SMTP HOST AND PORT MUST BE RELATIVE TO THE USED MAILING SERVICE
        smtp_host = data["email"]["sender-credentials"].get("smtp-host")
        smtp_port = data["email"]["sender-credentials"].get("smtp-port")

        if not smtp_host:  # IF NO SMTP HOST IS PROVIDED, USE GMAIL SMTP
            smtp_host = "smtp.gmail.com"
            smtp_port = 465

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp_server:
            smtp_server.login(
                data["email"]["sender-credentials"]["email"],
                data["email"]["sender-credentials"]["password"],
            )
            smtp_server.sendmail(
                data["email"]["sender-credentials"]["email"],
                attendee["email"],
                msg.as_string(),
            )
            print(f"CERTIFICATE {attendee_idx} SENT")

    except Exception as e:
        print(f"AN ERROR OCCURED WHEN SENDING CERTIFICATE {attendee_idx}: {e}")


def clear_run_output():
    """
    Deletes the 'output/<run-id>' generated directory.
    """

    try:
        shutil.rmtree(f".\\output\\{run_id}")
    except FileNotFoundError:
        print("RUN OUPTPUT DIRECTORY NOT FOUND")
    except Exception as e:
        print(f"AN ERROR OCCURED WHEN CLEARING RUN OUTPUT DIRECTORY: {e}")


def generate_and_send_certificates():
    """
    Generates and sends certificates by email to attendees using all the already provided data.
    """

    for attendee_idx, attendee in enumerate(attendees, start=1):
        generate_certificate(attendee_idx, attendee)

        if "send" in actions:
            send_certificate(attendee_idx, attendee)

    if args.clear_run_output or "save" not in actions and "send" in actions:
        clear_run_output()

    print(
        f"{len(attendees)} CERTIFICATE{'S' if len(attendees) > 1 else ''} PROCESSED SUCCESSFULLY"
    )


try:
    parser = argparse.ArgumentParser(description="Certificate Generator and Sender")
    parser.add_argument(
        "-a",
        "--actions",
        type=str,
        help="comma-separated list of actions to perform (preview, save, send), "
        "at least one of preview or save must be selected (save is the default action), "
        "example usage: --actions=save,send",
    )
    parser.add_argument(
        "-c",
        "--clear-run-output",
        action="store_true",
        help="delete the 'output/<run-id>' generated directory if send action was used, "
        "example usage: --clear-run-output",
    )

    args = parser.parse_args()
    actions = args.actions.split(",") if args.actions else ["preview"]

    with open(".\\data.json", encoding="utf-8") as data_file:
        data = json.load(data_file)

    template_filetype = data["template"]["filename"].split(".")[1]

    if template_filetype.lower() not in ["png", "jpg", "jpeg"]:
        raise FileFormatError("Template file must be in either PNG or JPG format.")

    font_filetype = data["template"]["styles"].get("font-filename", "").split(".")[1]

    if font_filetype.lower() not in ["ttf"]:
        raise FileFormatError("Font file must be in TTF format.")

    run_id = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{uuid.uuid4()}"

    print(f"RUN ID: {run_id}")

    attendees = get_attendees()

    generate_and_send_certificates()

except Exception as e:
    print(f"AN ERROR OCCURED: {e}")
