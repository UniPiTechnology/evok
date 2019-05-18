#############################################################################################################################
# Basic websocket application to interact with evok api                                                                     #
#   If You press a pushbutton which you connect to a digital input of you unipi                                             #
#    it toggles the corresponding relay on/off                                                                              #
#    you could see this as a direct swicth implementation                                                                   #
#    So e.g. : Digital Input 1 toggles Relay 1                                                                              #
#    I use a dictionary lookup for this(self.di_relay_dict)                                                                 #
#    So if you want another relay to switch on just change the second parameter for instance in 4 to swict on the 4 relay   #
#                                                                                                                           # 
#                                                                                                                           #
# Example create by Wim Stockman                                                                                            #   
#  On 2019-05-15                                                                                                            #
#############################################################################################################################



import websocket
import time
import json
def dprint(e):
    debug = 1
    if debug:
        print(e)
    

class myhome():
    def __init__(self):
        self.toggle_relay = 0
        self.di_relay_dict = {'1':'1','2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8'}

        self.ws = websocket.WebSocketApp("ws://192.168.1.102/ws",
                            on_message = lambda ws,msg: self.on_message(ws, msg),
                            on_error   = lambda ws,msg: self.on_error(ws, msg),
                            on_close   = lambda ws:     self.on_close(ws),
                            on_open    = lambda ws:     self.on_open(ws))
        self.ws.run_forever()
        
    def on_message(self,ws, message):
        try:
            j = json.loads(message)
            dprint(j)
        except:
            pass
        else:
            #check for digital input and button is pushed in
            if j['dev'] == 'input' and j['bitvalue'] == 1:
                  action = self.di_relay_dict.get(j['circuit'])

                # If the action is a digit toggle the relay with that number
                  if action.isdigit():
                        self.toggle_relay = 1
                        #we need to retrieve the current state of the relay so we set the toggle_relay to 1 to know we are expecting an answer on a question we asked
                        self.ws.send('{"cmd":"full","dev":"relay","circuit":"%s"}' %(j['circuit']))
                
            #check if we asked to toggle a relay if yes toggle it
            elif self.toggle_relay == 1 and j['dev'] == 'relay':
                self.toggle_relay = 0
                if j['value'] == 1:
                    ws.send('{"cmd":"set","dev":"relay","circuit":"%s","value":"0"}'%(j['circuit']))
                else:
                    ws.send('{"cmd":"set","dev":"relay","circuit":"%s","value":"1"}'%(j['circuit']))

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
