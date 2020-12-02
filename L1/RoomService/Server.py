#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import Ice, sys, json, os.path, logging, signal, random
Ice.loadSlice('Icegauntlet.ice')
import IceGauntlet

ROOMS_FILE = 'rooms.json'

class RoomServiceI(IceGauntlet.RoomService):
    '''pasar proxy authentication por parámetro desde run'''
    def __init__(self,authentication):
        self._rooms_ = {}
        self.authentication = authentication
        if os.path.exists(ROOMS_FILE):
            self.refresh()
        else:
            self.__commit__()

    def refresh(self):
        logging.debug('Reloading user database')
        with open(ROOMS_FILE,'r') as contents:
            self._rooms_ = json.load(contents)

    def __commit__(self):
        logging.debug('Room database updated!')
        with open(ROOMS_FILE,'w') as contents:
            json.dump(self._rooms_, contents, indent=4, sort_keys=True)

    def roomdataexists(self,data):
        for room in self._rooms_:
            if data == self._rooms_[room]['data']:
                return True
        return False

    def publish(self, token, roomData, current=None):
        '''check if user exists'''
        valid = self.authentication.isValid(token)
        if valid:
            '''Now, We gonna try to put roomData into a DB file'''
            '''Build the dictionary data'''
            contain = json.loads(roomData)
            if not contain['room'] and not contain['data']:
                raise IceGauntlet.InvalidRoom()
            nombre = contain['room']
            data = {
                'token': token,
                'data': contain['data']
            }
            self._rooms_[nombre] = data

            if self.roomdataexists(contain['data']):
                raise IceGauntlet.RoomAlreadyExists()
            else:
                self.__commit__()

        else:
            raise IceGauntlet.Unauthorized()
    
    def remove(self, token, roomName, current=None):
        ''''check if user exists'''
        valid = self.authentication.isValid(token)
        if valid:
            '''Now, We gonna try to remove roomData from a DB file'''
            '''Build the dictionary data'''
            #contain = json.loads(roomData)
            if self.roomdataexists(roomName):
                if self._rooms_[token]['token'] == token:
                    ROOMS_FILE.splice(roomName,1)
                    self.__commit__()
                else:
                    raise IceGauntlet.Unauthorized()
            else:
                raise IceGauntlet.RoomNotExists()

        else:
            raise IceGauntlet.Unauthorized()

class GameI(IceGauntlet.Game):

    def getRoom(self,current=None):
        map = ""
        with open(ROOMS_FILE,'r') as contents:
             data = json.load(contents)
             if len(data) == 0:
                 raise IceGauntlet.RoomNotExists()
             size = len(data)
             lab = random.randint(0,size) - 1
             i = 0
             for room in data:
                 if i == lab:
                     map = str(data[room]['data'])
                 else:
                     i+=1
        return map


class Server(Ice.Application):
    '''
    Authentication Server
    '''
    def run(self, argv):
        '''
        Server loop
        '''
        logging.debug('Initializing server...')
        '''check authentication proxy'''
        proxyauth = self.communicator().stringToProxy(argv[1])
        authentication = IceGauntlet.AuthenticationPrx.checkedCast(proxyauth)
        if not authentication:
            raise RuntimeError('Invalid proxy')

        servant = RoomServiceI(authentication)
        signal.signal(signal.SIGUSR1, servant.refresh)

        adapter = self.communicator().createObjectAdapter('RoomServiceAdapter')
#        proxy = adapter.add(servant, self.communicator().stringToIdentity('default'))
        proxy = adapter.addWithUUID(servant)
#        adapter.addDefaultServant(servant)
        #adapter.activate()
#        logging.debug('Adapter ready, servant proxy: {}'.format(proxy))
#        print('Proxy del RoomService: "{}"'.format(proxy), flush=True)

        servantGame = GameI()
#        signal.signal(signal.SIGUSR1, servantGame.refresh)
        proxy = adapter.addWithUUID(servantGame)
        adapter.activate()
        logging.debug('AdapterGame ready, servant proxy: {}'.format(proxy))
        print('Proxy: "{}"'.format(proxy), flush=True)

        logging.debug('Entering server loop...')
        self.shutdownOnInterrupt()
        self.communicator().waitForShutdown()

        return 0


if __name__ == '__main__':

    if len(sys.argv) != 3:
         print("usage: ./Server.py <proxy>")
         sys.exit(0)

    app = Server()
    sys.exit(app.main(sys.argv))
