#############################################################################################################################
#   Example 4: Basic websocket application to interact with evok api                                                        # 
#            Extension of the third  example websocket3                                                                     #        
#             Adding a book to trigger different action on multiple presses of each button separtly                         #
#                e.g. The first time, the first light switches on , the next time the second light goes on etc.             #
#                                                                                                                           #
#                                                                                                                           #    
#                I created for this basic example 3 commands you can use : - singletoggle (toggle one relay on or off)      #
#                                                                          - groupoff ( switch a group off relays off)      #
#                                                                          - groupon (switch a group off relay on)          #
#                                                                                                                           #
#                The groupon and groupoff function can be used for only 1 relay e.g. (1,) (don t forget the ","))           #                                                               
#                                                                                                                           #
#                In this example I also set long_press_action to groupoff. So you can control every light in serie          # 
#                If you have 3 lights and only want the middle one to be on, first time press long so the first light       #
#                switches on and off and press short and your second light is all_on                                        #
#                                                                                                                           #
#                                                                                                                           #
#                                                                                                                           #
#                                                                                                                           #
#                from the previous examples we also have allon (which turns all relays on) and alloff                       #
#                                                                                                                           #
#                                                                                                                           #
#                                                                                                                           #
#                                                                                                                           #
#                                                                                                                           #
#Long Press Button Event:                                                                                                   #
#                       I implemented this on the client side                                                               #
#                       We start a Timer (longpress timer) on a button press                                                #
#                       If the button is not released in 3 second we turn off all relays                                    #
#                       We achieve this to check inside the timer function if the long press is still active after 3s       #
#                       If the button is released before the 3 seconds are done we receive a message from the server        #
#                       signaling the button is released by sending a bitvalue of 0                                         #
#                        if we receive this message we set the long_press_button_active = 0                                 #
#                        and we set the long_press_timer = 0 so our Timer exits                                             #
#                                                                                                                           #
#                                                                                                                           #
#                                                                                                                           #
#                                                                                                                           #
# Example create by Wim Stockman                                                                                            #   
#  On 2019-05-21                                                                                                            #
#############################################################################################################################



import websocket
import time
import json
from threading import Thread


def dprint(e):
    debug = 0
    if debug:
        print(e)

    

class myhome():
    def __init__(self):
        #define in 1/10 of seconds
        self.WAITTIME = 10 

        self.long_press_timer_countdown = 0
        self.long_press_button_active = 0
        self.Timer = None

        self.toggle_relay = 0
        
        self.di_book = {'1':{'short_press_action':(
                                    ('singletoggle',1),
                                    ('singletoggle',2),
                                    ('singletoggle',3),
                                    ),
                             'long_press_action':(
                                 ('groupoff',(1,2,3))
                                 )
                            },
                        '2':{'short_press_action':(
                                    ('singletoggle',5),
                                    ),
                            'long_press_action':(
                                    ('groupoff',(5,))
                                    )
                            }

                        }

        for x in self.di_book:
           self.di_book[x]['step']=0   
           self.di_book[x]['maxstep'] = len(self.di_book[x]['short_press_action'])
        


        self.ws = websocket.WebSocketApp("ws://192.168.1.102/ws",
                            on_message = lambda ws,msg: self.on_message(ws, msg),
                            on_error   = lambda ws,msg: self.on_error(ws, msg),
                            on_close   = lambda ws:     self.on_close(ws),
                            on_open    = lambda ws:     self.on_open(ws))
        self.ws.run_forever()
        

    def long_press_timer(self,switch):
        dprint("Timer is Started")
        self.long_press_button_active = 1
        while self.long_press_timer_countdown > 0:
            time.sleep(.1)
            self.long_press_timer_countdown -= 1
            dprint(self.long_press_timer_countdown)
        if self.long_press_button_active:
            dprint(self.di_book[switch]['long_press_action'])
            long_press_action =  self.di_book[switch]['long_press_action'][0]
            if long_press_action == 'groupoff':
                group =  self.di_book[switch]['long_press_action'][1]
                dprint(group)
                self.groupoff(group)

        dprint("Timer Stopped")    

    def groupon(self,group):
        for e in group:
                dprint(e)
                self.ws.send('{"cmd":"set","dev":"relay","circuit":"%s","value":"1"}'%(e))
                time.sleep(0.05)

    def groupoff(self,group):
        for e in group:
                dprint(e)
                self.ws.send('{"cmd":"set","dev":"relay","circuit":"%s","value":"0"}'%(e))
                time.sleep(0.05)

    def singletoggle(self,switch,relay_answer=None):
        dprint(self.toggle_relay)

        if self.toggle_relay == 0:
            dprint("inside routine singletoggle")
            self.toggle_relay = 1
            self.ws.send('{"cmd":"full","dev":"relay","circuit":"%s"}' %(switch))
        else:
            dprint("second time")
            dprint(relay_answer)
            if relay_answer['value'] == 1 and switch == relay_answer['circuit']:
                dprint("swichtoff")
                self.toggle_relay = 0
                self.ws.send('{"cmd":"set","dev":"relay","circuit":"%s","value":"0"}'%(relay_answer['circuit']))

            elif relay_answer['value'] == 0 and switch == relay_answer['circuit']:
                dprint("swicht On")
                self.toggle_relay = 0
                self.ws.send('{"cmd":"set","dev":"relay","circuit":"%s","value":"1"}'%(relay_answer['circuit']))






    def on_message(self,ws, message):
        try:
            j = json.loads(message)
            dprint(j)
        except:
            pass
        else:
            if j['dev'] == 'input' and j['bitvalue'] == 0:
                self.long_press_timer_countdown = 0
                self.long_press_button_active = 0
                 
                #check for digital input and button is pushed in
            elif j['dev'] == 'input' and j['bitvalue'] == 1:
                    self.long_press_timer_countdown = self.WAITTIME
                       
                    self.Timer = Thread(target = self.long_press_timer, args=(j['circuit'],))
                    self.Timer.start()
                      
                    digital_input_number = str(j['circuit'])
                    
                    #lookup in our dictionary what appropriate action to take for this digital input
                    step = self.di_book[digital_input_number]['step']
                    short_press_action =  self.di_book[digital_input_number]['short_press_action'][step][0]
                    switch = self.di_book[digital_input_number]['short_press_action'][step][1]
                    if short_press_action == 'singletoggle':
                        dprint('Single Toggle')
                        dprint(switch)
                        dprint(step)
                        dprint(self.di_book[digital_input_number]['maxstep'])
                        self.singletoggle(switch)
                        self.di_book[digital_input_number]['step'] +=1
                        if self.di_book[digital_input_number]['step'] >= self.di_book[digital_input_number]['maxstep']:
                            self.di_book[digital_input_number]['step'] = 0

                    elif short_press_action == 'groupon':
                        self.groupon(switch)
                        self.di_book[digital_input_number]['step'] +=1
                        if self.di_book[digital_input_number]['step'] >= self.di_book[digital_input_number]['maxstep']:
                            self.di_book[digital_input_number]['step'] = 0
                    
                    elif short_press_action == 'groupoff':
                        self.groupoff(switch)
                        self.di_book[digital_input_number]['step'] +=1
                        if self.di_book[digital_input_number]['step'] >= self.di_book[digital_input_number]['maxstep']:
                            self.di_book[digital_input_number]['step'] = 0

            elif j['dev'] == 'relay' and self.toggle_relay:
                        dprint("relay answer")
                        self.singletoggle(j['circuit'],j)




                  


    def all_on(self):
        for x in range (1,9):
            self.ws.send('{"cmd":"set","dev":"relay","circuit":"%s","value":"1"}' %(x))
            time.sleep(0.05)
    def all_off(self):
        for x in range (1,9):
            self.ws.send('{"cmd":"set","dev":"relay","circuit":"%s","value":"0"}' %(x))
            time.sleep(0.05)

    def on_error(self,ws, error):
        print(error)

    def on_close(self,ws):
        print ("### closed ###")
              

    def on_open(self,ws):
        print ("### opened ###")
        # just wait half a second to give the server some time
        time.sleep(.5)




if __name__ == "__main__":
    app= myhome()
