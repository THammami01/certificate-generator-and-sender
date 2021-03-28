import bcrypt
import uuid
import csv
from typing import Any
from pathlib import Path
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


class PW:
    """Class for hashing and verifying passwords."""
    def hash(passwd):
        """Method that returns a hash from a plain password.
        @param passwd: password to hash
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(passwd, salt)

    def verify(passwd, hashed) -> bool:
        """Method that checks if a given password and a hashed one match
        @param passwd: Given password
        @param hashed: Saved hash
        """
        return bcrypt.checkpw(passwd, hashed)


# def test_pw() -> None:
#     passwd = b"secret"  # or "secret".encode('utf-8')
#     print(PW.verify(b"secret", PW.hash(passwd)))


def getReceiversFromCsv(fileName: str) -> list[dict[str, str]]:
    """Function that gets receivers data from a .csv file and returns a list.
    @param fileName: name of the .csv file, must be included in '.\\receivers\\'
    """

    receivers: list[dict[str, str]] = []
    with open(f".\\receivers\\{fileName}") as csvFile:
        csvReader = csv.reader(csvFile, delimiter=',')
        isFirstRow: bool = True
        for row in csvReader:
            receivers.append({"fullName": row[0], "email": row[1]})
    return receivers


def processBody(receiver: dict[str, str], body: str) -> str:
    """Method for processing email body and replacing all keywords (starting with $) with equivalent receiver's data.
    @param receiver: receiver's email and full name
    @param body: body of the email before processing
    """

    for key in receiver:
        body: str = body.replace(f"${key}", receiver[key])
    return body


def make_certificate(receiverId: int, fullName: str, preview: bool = True) -> None:
    """Function for creating a certificate. Saved in '.\output\[uniqueId]\'
    @param receiverId: receiver's id
    @param fullName: receiver's fullname
    @param preview: whether to preview the certifacate or not after generating it
    """

    # Make sure path and its parents exist
    Path(f".\\output\\{uniqueId}").mkdir(parents=True, exist_ok=True)

    image = cv2.imread(f".\\templates\\{template}")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(image)
    draw = ImageDraw.Draw(image)

    nameFont = ImageFont.truetype(
        f".\\fonts\\{nameStyle['font-family']}.ttf", nameStyle['font-size'])

    # In order to center the text as required
    w, h = draw.textsize(fullName, nameFont)
    nameLeft = (image.width - w) / 2

    draw.text((nameLeft, nameStyle["coords"]["top"]),
              fullName, font=nameFont, fill=nameColor)

    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    cv2.imwrite(f".\\output\\{uniqueId}\\{receiverId}.{extension}", image)
    if(preview):
        cv2.imshow(imgNameToSend, image)
        cv2.waitKey()

    print(f"Certificate {receiverId} generated.")


def send_emails(testing=True) -> None:
    """Function for sending emails using all the already provided data."""

    receiverId: int = 0
    for receiver in receivers:
        receiverId += 1
        if(not testing):
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = senderEmail
            msg['To'] = receiver["email"]
            bodyProcessed: str = processBody(receiver, body)
            msgText = MIMEText(bodyProcessed, 'html')
            msg.attach(msgText)

            make_certificate(receiverId, receiver["fullName"], preview=False)

            with open(f".\\output\\{uniqueId}\\{receiverId}.{extension}", "rb") as fp:
                img = MIMEImage(fp.read())
                img.add_header('Content-Disposition', 'attachment',
                            filename=imgNameToSend)
                msg.attach(img)

                try:
                    # SMTP host and port must be relative to the used mailing service
                    with smtplib.SMTP('smtp.gmail.com', 587) as smtpObj: 
                        smtpObj.ehlo()
                        smtpObj.starttls()
                        smtpObj.login(senderEmail, senderPassword)
                        smtpObj.sendmail(
                            senderEmail, receiver["email"], msg.as_string())
                        print(f"Certificate {receiverId} sent.")
                except Exception as e:
                    print(e)
        else:
            make_certificate(receiverId, receiver["fullName"], preview=False)

    if(not testing):
        print(f"{len(receivers)} certificate{'s' if len(receivers) > 1 else ''} generated and sent successfully.")
    else:
        print(f"{len(receivers)} certificate{'s' if len(receivers) > 1 else ''} generated successfully.")


# Required details in order to successfully generate certificates and send them by email
# uniqueId: str = "gestion-d-equipe"  # Unique ID for each certificate, must be encoded in ASCII
# uniqueId: str = "developpement-mobile"
uniqueId: str = "test"
senderEmail: str = "Maseer.isetbj@gmail.com"
senderPassword: str = "xxxxxxxx"
subject: str = "Certificat de participation"
body: str = "Bonsoir <em>$fullName</em>.<br/>Notre équipe de <b>Maseer iset beja</b> vous remercions très sincèrement pour votre participation à notre formation en ligne.<br/>Cordialement."
imgNameToSend: str = "Certificat de participation"
receivers: list[dict[str, str]] = getReceiversFromCsv(f"{uniqueId}.csv")

extension: str = "png"
template: str = f"{uniqueId}.{extension}"  # Must be included in '.\templates\'
nameStyle: dict[str, Any] = { 
    "font-family": "Roboto-Light",  # Font must be included in '.\fonts\'
    
    # "font-size": 90,
    # "font-size": 90,
    "font-size": 90,

    # "coords": {"top": 580, "offset": 0}  # Coordinates must be calculated mannually
    # "coords": {"top": 640, "offset": 0}
    "coords": {"top": 640, "offset": 0}
}
nameColor = "#767676"


send_emails(testing=False)  # Generate and send emails
