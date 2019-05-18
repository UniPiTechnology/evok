#############################################################################################################################
#   Example 2: Basic websocket application to interact with evok api                                                        # 
#            Extension of the first example websocket1                                                                      #        
#            We add a All relays on button on digital input  1                                                              #               
#            We add a All relays off button on digital input 2                                                              #
#     In the all_on all_off we need to add some delay to give the server some time to react  !!!                            #
#       or strange behavior occurs!!                                                                                        # 
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
        self.di_relay_dict = {'1':'allon','2':'alloff','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8'}

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
                  #if the action is allon switch all relays on                         
                  elif action == 'allon':
                      self.all_on()
                  elif action == 'alloff':
                      self.all_off()

            #check if we asked to toggle a relay if yes toggle it
            elif self.toggle_relay == 1 and j['dev'] == 'relay':
                self.toggle_relay = 0
                if j['value'] == 1:
                    ws.send('{"cmd":"set","dev":"relay","circuit":"%s","value":"0"}'%(j['circuit']))
                else:
                    ws.send('{"cmd":"set","dev":"relay","circuit":"%s","value":"1"}'%(j['circuit']))

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
