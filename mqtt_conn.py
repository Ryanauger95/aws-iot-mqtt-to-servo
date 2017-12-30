#
#   Author: Ryan Auger
#   Purpose:
#       Control Servo Motor With MQTT
#

#Import SDK packages
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from time import sleep
import RPi.GPIO as GPIO
import sys


# GPIO Setup
#   GPIOPin - Pin on the raspberry pi that is controlling the servo
#   PulseFrequency- Frequency of the pulses sent to the servo
#                   The servo expects a pulse every 20ms for between 1ms and 2ms
#                   1ms corresponds to an angle of 0 degrees, while a pulse of 2ms
#                   corresponds to an angle of 180 degrees
#                   - A value of 100(Hz) means that the Pi will send a pulse 100 times per 
#                   second, or once every 10ms.
#
#   PWM0 - The percentage of time that GPIO pin must be "ON" so that 
#           the motor will turn to angle 0
#           The equation for finding the Correct PWM0, or the pulse modulation 
#                     Required to set the servo to angle 0 is:
#                         DutyCycle = PW/T * 100%
#                         D=1ms/20ms*100 = 5
#           For the motor that I am using (FS5106B), the angles are a bit funky, and 
#           I had to increase the Duty Cycle to 6.5
#
GPIOPin=7
PulseFrequency=100
PWM0=6.50
PWC=PWM0*2
PWM90=PWM0*2
PWM180=PWM0*3


# Set the pinout type to board to use standard board labeling
#
GPIO.setmode(GPIO.BOARD)
GPIO.setup(GPIOPin, GPIO.OUT)
p = GPIO.PWM(GPIOPin, PulseFrequency)


# Set MQTT parameters
# Part 1: Group identifier - helps denote groups of IoT devices
# Part 2: UUID - individual device identifier
# Part 3: DT/MT/ST - Device Terminated, Mobile Terminated, or Server Terminated - Which element
#                   in our MQTT system should get the message?
# Part 4: CMD/CTRL - Helps separate different types of messages for code clarity
#   - Parts 3&4 combine to form the "Channel"
UUID = "0001"
FLEET = "test"
SUB_CHANNEL = "DT/CMD"
PUB_CHANNEL = "MT/CMD"  # For sending messages back to a mobile device
SubTopic = "%s/%s/%s" % (FLEET, UUID, SUB_CHANNEL)
PubTopic = "%s/%s/%s" % (FLEET, UUID, PUB_CHANNEL)


# AWS Authentication Credentials
# https://github.com/aws/aws-iot-device-sdk-python 
Host = "a9axurntd49mw.iot.us-east-1.amazonaws.com"
Port = 8883
CaCert = "/home/pi/repos/shower_head/certs/ca.crt"
Key = "/home/pi/repos/shower_head/certs/priv.key"
Cert = "/home/pi/repos/shower_head/certs/cert.crt"


# Used to control Motor on/off
State = 1
Subscribing = 1


#For certificate based connection
myMQTTClient = AWSIoTMQTTClient(UUID)
# For TLS mutual authentication
myMQTTClient.configureEndpoint(Host, Port)
myMQTTClient.configureCredentials(CaCert, Key, Cert)
myMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec


# Called whenever a message is published to a topic that you are subscribed to
# Do any logic in a block like this
def cmd_callback ( Client, UserData, Message ):
    # Read in global variable
    global State

    # Parse the MQTT Message
    Topic = Message.topic                
    Payload = Message.payload.split(";")
    Command = Payload[0]

    print "Message: %s from Topic: %s" % (Payload, Topic)
    
    #Handle Message
    if  (
        Command == "SHOWER ON" #Start Motor
        ):    
        print "Starting Motor"
        p.start(PWM0) 
        sleep(1)
    elif(
        Command == "ROTATE" and 
        float(Payload[1]) <= 180 and 
        float(Payload[1]) >= 0 
        ):
        
        Angle=float(Payload[1])
        print "Setting Motor to Angle: %s " % Angle
        Duty = (Angle / 180) * PWC + PWM0  
        GPIO.output(7, True)
        p.ChangeDutyCycle(Duty) 

    elif Command == "SHOWER OFF":
        print "Returning Motor to Position Off Position"
        p.stop()
        State = 0

def cleanup () :
    myMQTTClient.unsubscribe(SubTopic)
    myMQTTClient.disconnect()
    p.stop()
    GPIO.cleanup() 


# Initialize connection and subscription
# The function "cmd_callback" will be called whenever a message is
# published to the subscribe topic
print "Connecting to host: %s on port %d" % (Host, Port)
myMQTTClient.connect()
print("Subscribing to topic: %s and entering loop waiting for messages" % SubTopic)
myMQTTClient.subscribe(SubTopic, 1, cmd_callback)

# Enter a subscribe loop.
try:
    while 1:
        if State == Subscribing:
            sleep(1)
        else:
            cleanup()
            sys.exit()

except KeyboardInterrupt:
    p.stop()
    GPIO.cleanup()




 
