
import datetime
import email
import os
import imaplib
from time import sleep
from threading import Thread
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.message import EmailMessage
import re
import pdb
#Fri May 24 15:51:32 2019

class EmailSniffer():

    def __init__(self,
                 email_account,
                 username=None, pw=None,
                 check_rate_min=1,
                 imap_svr=None, imap_port=None,
                 smtp_svr=None, smtp_port=None,
                 imei=None,
                 arrival_email_filt=None,
                 attachment_ext_filt=None):
        self.IMEI = imei
        self.SENDER = arrival_email_filt
        #self.SENDER='RockBLOCK'
        self.FROM = email_account
        self.email_username = username
        self.email_pw = pw
        self.email_check_rate = check_rate_min
        self.email_incoming_svr = imap_svr
        self.email_outgoing_svr = smtp_svr
        self.email_incoming_port = imap_port
        self.email_outgoing_port = smtp_port
        self.attachment_ext_filt = attachment_ext_filt

        self.EMAILTEXT = "MOMSN: {0}\nMTMSN: 0\nTime of Session (UTC): {1}\nSession Status: 00 - Transfer OK\nMessage Size (bytes): {2}"
        self.momsn = 900000

        self.incoming_attachment_queues = []

        #self.last_read = datetime.datetime.now()
        self.last_read = datetime.datetime.utcnow()
        self.alive = True

        self._threadL = Thread(target=self._listen)
        self._threadL.setDaemon(True)
        self._threadL.start()

    def _listen(self):
        print('Listen thread started')
        while self.alive:
            try:
                date = (datetime.datetime.now() - datetime.timedelta(hours=72)).strftime("%d-%b-%Y")

                M = imaplib.IMAP4(self.email_incoming_svr)

                response, details = M.login(self.email_username, self.email_pw)
                M.select('INBOX/ignored')
                #M.select('INBOX')
                #pdb.set_trace()

                print('Checking INBOX/ignored')
                #Search for messages in the past hour with subject line specified and from sender specified
                #response, items = M.search(None,
                #                           '(UNSEEN SENTSINCE {date} HEADER Subject "{subject}" FROM "{sender}")'.format(
                #                               date=date,
                #                               subject=self.IMEI,
                #                               sender=self.SENDER
                #                           ))
                # note need to change back to UNSEEN for real code
                response, items = M.search(None,
                                           '(UNSEEN SENTSINCE {date} HEADER Subject "{subject}" FROM "{sender}")'.format(
                                               date=date,
                                               subject=self.IMEI,
                                               sender='RockBLOCK'
                                           ))
                #print(response)
                #print(items)
                #pdb.set_trace()
                for emailid in items[0].split():
                    response, data = M.fetch(emailid, '(RFC822)')

                    mail = email.message_from_string((data[0][1]).decode('utf-8'))
                    #
                    junk=data[0][1].decode('utf-8')
                    latindex=[m.start() for m in re.finditer('Latitude:',junk)]
                    lonindex=[m.start() for m in re.finditer('Longitude:',junk)]
                    dateindex=[m.start() for m in re.finditer('Date:',junk)]
                    latitude=junk[latindex[0]+10:latindex[0]+17]
                    longitude=junk[lonindex[0]+11:lonindex[0]+20]
                    adates=junk[dateindex[1]+11:dateindex[1]+31]
                    adateobj=datetime.datetime.strptime(adates,'%d %b %Y %H:%M:%S')
                    offset=datetime.datetime(1970,1,1)
                    timeformail=(adateobj-offset).total_seconds()
                    # this is the code to send to ODSS
                    # commented out for now
                    #if (longitude < -121.7885) and (longitude > -122.166):
                    mymsg=EmailMessage()
                    mymsg['Subject']='Emperor,'+str(timeformail)+','+str(longitude)+','+str(latitude)
                    mymsg['From']='flbahr@mbari.org'
                    mymsg['To']='auvtrack@mbari.org'
                    mymsgtxt='Emperor,'+str(timeformail)+','+str(longitude)+','+str(latitude)
                    mymsg.set_payload(mymsgtxt)
                    stest=smtplib.SMTP('localhost')
                    stest.send_message(mymsg)
                    stest.quit()
                    # mail message to tracking database
                    # To: auvtrack@mbari.org
                    # From: usv_track
                    # Subject:Emporor,time,long,lat
                    # body Emporor,time,lon,lat
                    

                    if not mail.is_multipart():
                        #print('Is not multipart')
                        x1=mail.get('Content-Disposition')
                        #print('Content')
                        #print(x1)
                        x2=mail.get_filename()
                        #print('file name')
                        #print(x2)
                        x3=mail.get_payload(decode=True)
                        #print('payload')
                        #print(x3)
                        continue
                    for part in mail.walk():
                        #pdb.set_trace()
                        x1=part.get('Content-Disposition')
                        #print('Content')
                        #print(x1)
                        x2=part.get_filename()
                        #print('file name upper')
                        #print(x2)
                        x3=part.get_payload(decode=True)
                        #print('payload')
                        #print(x3)
                        
                        if part.is_multipart() and x2 is None:
                            print('is multipart')
                            continue
                        if x1 is None:
                            continue
                        #if part.get('Content-Disposition') is None:
                        #    continue
                        file_nm = part.get_filename()
                        #print('File name lower')
                        #print(file_nm)
                        if x2 is None:
                        #if file_nm is None:
                            continue
                        #print('Got filename')
                        filename, fileext = os.path.splitext(file_nm)
                        #print(filename)
                        msg=part.get_payload(decode=True)
                        #print(msg)
                        #print('File extension')
                        #print(fileext)
                        #pdb.set_trace()
                        if self.attachment_ext_filt is not None:
                            if fileext != self.attachment_ext_filt:
                                continue
                        msg = part.get_payload(decode=True)

                        #print('Found msg in INBOX')
                        #print(msg)
                        #pdb.set_trace()
                        sleep(1)
                        for q in self.incoming_attachment_queues:
                            q.put_nowait(msg)
                            sleep(5)

                        temp = M.store(emailid, '+FLAGS', '\\Seen')
                    #pdb.set_trace()
                M.close()
                M.logout()
                #pdb.set_trace()
                sleep(self.email_check_rate * 60)
            except:
                # Could probably handle this better, but just so we don't kill the thread...
                print('Failed to access email')
                pass

    def write(self, msg):
        print('Writing e-mail')
        email_msg = MIMEMultipart()
        email_msg['Subject'] = "SBD Msg From Unit: " + "{0}".format(self.IMEI)
        email_msg['To'] = self.SENDER
        email_msg['From'] = self.FROM

       #part = MIMEText(self.EMAILTEXT.format(self.momsn, datetime.datetime.now().ctime(), len(msg)))
        part = MIMEText(self.EMAILTEXT.format(self.momsn, datetime.datetime.utcnow().ctime(), len(msg)))

        email_msg.attach(part)

        attachment = MIMEApplication(msg)

        attachment.add_header('Content-Disposition', 'attachment',
                              filename="{0}_{1}{2}".format(self.IMEI, self.momsn,
                                                            self.attachment_ext_filt))
        email_msg.attach(attachment)
        print('SMTP connect')
        print(self.email_outgoing_svr)
        print(self.email_outgoing_port)
        smtp = smtplib.SMTP('mbarimail.mbari.org', self.email_outgoing_port)
        #smtp = smtplib.SMTP('outbox.whoi.edu', self.email_outgoing_port)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(self.email_username, self.email_pw)
        print('SMTP send')
        smtp.sendmail(self.FROM, [email_msg['To'], self.FROM], email_msg.as_string())
        print('SMTP quit')
        smtp.quit()

        self.momsn = self.momsn + 1

    def close(self):
        self.alive = False

    def append_incoming_attachment_queue(self, queue_to_append):
        self.incoming_attachment_queues.append(queue_to_append)
