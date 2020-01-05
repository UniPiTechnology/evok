#############################################################################################################################
#   Example 5: Basic websocket application to interact with evok api
#		Fully Function Basic websocket application to interact with the evok api 
#               This is a how the lights are switched in our house in real live 
#
#			Every Input can have a short_press_action and a long_press_action 
#			inside those two actions you can use 
#                                                                                                                           #    
#                				  3 commands  : - singletoggle (toggle one relay on or off)   		    #
#                                                               - groupoff ( switch a group off relays off)                 #
#                                                               - groupon (switch a group off relay on)                     #
#                                                                                                                           #
#                The groupon and groupoff function can be used for only 1 relay e.g. (1,) (don t forget the ","))           #                                                               
#                                                                                                                           #
                                                                                                                            #
#                                                                                                                           #
#                                                                                                                           #
#                                                                                                                           #
#                												            #
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
#  Changed for Neuron on 2019-09-28                                                                                         # 
#                                                                                                                           #
#                                                                                                                           #
#                                                                                                                           #
# On 2019-10-07                                                                                                             #    
# Updated singletoggle to work on longpress action                                                                          #        
#                                                                                                                           #
# On 2020-01-05                                                                                                             #
# Updated added SIGINT CTRL-C signal handling to stop the keepalive thread                                                  #     
# The keepalive thread check every 10 s if the noexit variable is still thrue otherwise we end the loop                     #
# and so ends the thread                                                                                                    #
#                                                                                                                           #
#############################################################################################################################



import websocket
import time
import json
from threading import Thread
from signal import signal,SIGINT
from sys import exit


def dprint(e):
    debug = 0
    if debug:
        print(e)

    

class myhome():
    def gracefull_shutdown(self,signal_received,frame):
        print('SIGINT or CTRL-C detected. Exiting gracefully')
        self.ws.close()
        print('Exting All current Threads this takes maximum 10 seconds')
        self.noexit = 0
        exit()

    def __init__(self):
        signal(SIGINT, self.gracefull_shutdown)
        #define in 1/10 of seconds
        self.WAITTIME = 10 

        self.long_press_timer_countdown = 0
        self.long_press_button_active = 0
        self.Timer = None
        self.KeepaliveTimer = None
        self.noexit = 1;
        self.toggle_relay = 0
        
        self.di_book = {
                        '3_09':{'short_press_action':(
                                    ('singletoggle','3_04'),
                                    ),
                            'long_press_action':(
                                    ('groupoff',(5,))
                                    )
                               },
                        '3_10':{'short_press_action':(
                                    ('singletoggle','3_05'),
                                    ),
                             'long_press_action':(
                                 ('groupoff',('3_05','3_04','UART_15_2_08','UART_15_2_07'))
                                 )
                               },
                        '3_11':{'short_press_action':(
                                    ('singletoggle','UART_15_2_08'),
                                    ),
                            'long_press_action':(
                                    ('groupoff',(5,))
                                    )
                               },
                        '3_12':{'short_press_action':(
                                    ('singletoggle','UART_15_2_07'),
                                    ),
                            'long_press_action':(
                                    ('groupoff',(5,))
                                    )
                               },
                        '3_13':{'short_press_action':(
                            ('singletoggle','3_05'),
                            ),
                             'long_press_action':(
                                 ('groupoff',('3_05','UART_15_2_07','UART_15_2_08'))
                                 )
                               },
                        '3_14':{'short_press_action':(
                            ('singletoggle','UART_15_2_07'),)
                               },
                        '3_15':{'short_press_action':(
                            ('singletoggle','3_03'),
                            ),
                                'long_press_action':(
                                    ('singletoggle','UART_15_2_08'),
                                    ),
                               },
                        '3_16':{'short_press_action':(
                            ('singletoggle','3_01'),),
                               },
                        '2_13':{'short_press_action':(
                            ('singletoggle','3_08'),('singletoggle','3_09'),
                            ),
                             'long_press_action':(
                                 ('groupoff',('3_08','3_09'))
                                 )
                               },
                        '3_02':{'short_press_action':(
                            ('groupon',('UART_15_2_07','UART_15_2_08')),
                                ),'long_press_action':(
                            ('groupoff',('2_03','2_04','2_13','2_14','3_01','3_03','3_04','3_05','3_08','3_09','UART_15_2_01','UART_15_2_06','UART_15_2_07','UART_15_2_08')))
                               },
                        '3_03':{'short_press_action':(
                            ('singletoggle','2_13'),)
                               },
                        'UART_15_2_04':{'short_press_action':(
                            ('singletoggle','2_03'),)
                               },
                        '2_11':{'short_press_action':(
                            ('singletoggle','2_04'),)
                               },
                        'UART_15_2_08':{'short_press_action':(
                            ('singletoggle','UART_15_2_06'),)
                               },
                        '2_06':{'short_press_action':(
                            ('singletoggle','2_04'),)
                               },
                        '2_07':{'short_press_action':(
                            ('singletoggle','UART_15_2_01'),)
                               },
                        '3_08':{'short_press_action':(
                            ('singletoggle','2_14'),)
                               },
                        '2_04':{'short_press_action':(
                            ('singletoggle','2_04'),),
                               },
                        '2_09':{'short_press_action':(
                            ('singletoggle','3_03'),),
                               },
                             'UART_15_2_14':
                                {'short_press_action':(
                                ('groupon',('3_01','3_03','3_05','3_08','3_09')),
                                ),'long_press_action':(
                            ('groupoff',('2_03','2_04','2_13','2_14','3_01','3_03','3_04','3_05','3_08','3_09','UART_15_2_01','UART_15_2_06','UART_15_2_07','UART_15_2_08')))
                               }
}

        for x in self.di_book:
           self.di_book[x]['step']=0   
           self.di_book[x]['maxstep'] = len(self.di_book[x]['short_press_action'])
        


        self.ws = websocket.WebSocketApp("ws://localhost/ws",
                            on_message = lambda ws,msg: self.on_message(ws, msg),
                            on_error   = lambda ws,msg: self.on_error(ws, msg),
                            on_close   = lambda ws:     self.on_close(ws),
                            on_open    = lambda ws:     self.on_open(ws))
        self.ws.run_forever()

    def keepalive(self):
        i = 0
        while self.noexit:
            dprint("Keep Alive")
            if i > 5:
                self.ws.send('{"cmd":"full","dev":"relay","circuit":"3_01"}')
                i = 0
            time.sleep(10) 
            i += 1

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
            if self.di_book[switch]['long_press_action'][0][0] == 'singletoggle' :
                single =  self.di_book[switch]['long_press_action'][0][1]
                dprint('LONG PRESS SINGLE')
                dprint(single)
                self.singletoggle(single)
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
            if isinstance(j,list):
	       dprint(type(j))
	       j = j[0]
            dprint(j)
        except:
            pass
        else:
	    if j['dev'] == 'input' and j['value'] == 0:
                self.long_press_timer_countdown = 0
                self.long_press_button_active = 0
                dprint("gesloten")
                #check for digital input and button is pushed in
            elif j['dev'] == 'input' and j['value'] == 1:
                    self.long_press_timer_countdown = self.WAITTIME
                    dprint("Wim") 
                    self.Timer = Thread(target = self.long_press_timer, args=(j['circuit'],))
                    self.Timer.start()
                      
                    digital_input_number = j['circuit']
		    dprint(digital_input_number)
                    
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
        ws.close()
        print ("### closed ###")
              

    def on_open(self,ws):
        print ("### opened ###")
        # just wait half a second to give the server some time
        time.sleep(.5)
        self.KeepaliveTimer = Thread(target = self.keepalive,)
        self.KeepaliveTimer.start()


if __name__ == "__main__":
    app= myhome()

