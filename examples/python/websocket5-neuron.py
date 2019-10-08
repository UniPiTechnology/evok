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
#  On 2019-05-21                          
#  Changed for Neuron on 2019-09-28 
#
#
#
# On 2019-10-07
# Updated singletoggle to work on longpress action
#
#############################################################################################################################



import websocket
import time
import json
from threading import Thread

                                                                                                                                                                                                                            52,0-1        Top

