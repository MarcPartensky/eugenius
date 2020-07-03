# Eugenius
Eugenius is a simple Python module that can automate the actions you can do on the [Eugénie](https://www.nexity.fr/eugenie "Eugénie") application.
Engenius can control all accessible devices for the Eugénie application. This module is useless if your home is not compatible with Eugénie.

## What you need to use Eugenius
- To have a Eugénie account that can control your house with the application
- Basic Python knowledge
## Installation

You need first to install [warrant](https://github.com/capless/warrant "warrant") with `pip install warrant`.

Then copy  `Eugenius.py` of this repository in your Python project.

To import Eugenius from your project :
```python
from Eugenius import Eugenius
```

## Feature

It all depends on what you can do with your basic Eugenie application but generally you will be able to :

- Control your lights in your home
- Control your shutters of your home
- Adjust the thermostats of your radiators

All this with Python.

## Usage

First do an instance of the module, you need to pass your Eugénie account info
```python
eug = Eugenius("YourEugénieEmail", "YourEugéniePassword")
```

Then you can get your `Home` instance :
```python
home = eug.getHome()
```

### Home instance
##### Get the list of devices you can control
```python
home.devices
```

### Device

#### Generality
```python
device = home.devices[0] #Let's take the first device
device.available # bool
device.enabled # bool
device.label #Name of the device in Eugénie app
device.controllableName #interesting name
device.oid
device.placeOID
device.uiClass
```
For each different `controllableName`, there are different possible commands.


#### List of main commands for the controllable io:RollerShutterGenericIOComponent
```python
assert device.controllableName=="io:RollerShutterGenericIOComponent"
device.exec("open") #fully opens the shutter
device.exec("close") #fully closes the shutter
device.exec("setDeployment", 90) #closes 90% of the shutters
```

#### List of main commands for the controllable zwave:OnOffLightZWaveComponent

```python
assert device.controllableName=="zwave:OnOffLightZWaveComponent"
device.exec("off") #swith off the light
device.exec("on") #switch on the light
device.exec("setOnOff","on") #switch on the light also works with "off"
secondsToWait=5 #secondsToWait must be an int between 5 and 14400
device.exec("onWithTimer", secondsToWait) #If the light is off, it will come on instantly. If the light is on, it will turn off after 5 seconds.

```

#### Get all available commands for a device

```python
device = home.devices[0] #Let's take the first device
device.commands #return a dict where keys are commands (str) and value are number of param to execute the command
```

With a light (zwave:OnOffLightZWaveComponent) :
```python
device.commands
#{'close': 0, 'delayedStopIdentify': 1, 'down': 0, 'getName': 0, 'identify': 0, 'my': 0, 'open': 0, 'refreshMemorized1Position': 0, 'setClosure': 1, 'setDeployment': 1, 'setMemorized1Position': 1, 'setName': 1, 'setPosition': 1, 'setSecuredPosition': 1, 'startIdentify': 0, 'stop': 0, 'stopIdentify': 0, 'up': 0, 'wink': 1}
```

### States
Device can have multiple states. States are useful if you want, for example, check if a light is on.
```python
device.states #return states of device
#it's a dict where keys are names of state and value are state object
```

The possible attributes of a state :
```python
state.qualifiedName #the name of the state, always defined
state.type # may be 'DiscreteState' or 'ContinuousState', always defined
state.value #the current value of the state, sometimes not defined
state.values #the values that value can take, sometimes not defined
```

#### Example with a zwave:OnOffLightZWaveComponent

```python
device.controllableName # 'zwave:OnOffLightZWaveComponent'
device.states
# {'core:DeviceDefectState': <State object at 0x05CFD310>, 'core:NeighboursAddressesState': <State object at 0x05CFD328>, 'core:OnOffState': <State object at 0x05CFD340>}
device.states['core:OnOffState'].value # 'on' because my light is on
device.states['core:OnOffState'].values # ['off','on']
device.states["core:OnOffState"].type # 'DiscreteState'
device.states['core:OnOffState'].qualifiedName # 'core:OnOffState'
```

### Device URL
Once you have retrieved the device you want to control, you can retrieve its url with :
```python
device.deviceURL #return a unique URL for each device
```
This URL is permanent. You can retrieve the device associated with this URL with :
```python
home.getDeviceByURL[device.deviceURL]
```

### When you're done
Eugenius's instance use a thread to stay connected to the servers.
When you're done, you should kill the thread like this :
```python
eug.disconnect()
```