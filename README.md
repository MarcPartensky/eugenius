# Eugenius
Eugenius is a Python module that can roughly replace the app [Eugénie](https://www.nexity.fr/eugenie "Eugénie").
Engenius can control all accessble devices for the Eugénie application. This module is useless if your home is not compatible with Eugénie.


## What you need to use Eugenius
- To have a Eugénie account that can control your house with the application

## Installation

You need first to install [warrant](https://github.com/capless/warrant "warrant")

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


## Usage

First do an instance of the module, you need to pass your Eugénie account info
```python
eug = Eugenius("email", "password", "clientID")
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
device.label #Name of the device in Eugénie app
device.controllableName #interesting name 

```
For each different `controllableName`, there are different possible commands.




#### List of main commands for io:RollerShutterGenericIOComponent
```python
assert device.controllableName=="io:RollerShutterGenericIOComponent"
device.exec("open") #fully opens the shutter
device.exec("close") #fully closes the shutter
device.exec("setDeployment", 90) #closes 90% of the shutters
```

#### List of main commands for zwave:OnOffLightZWaveComponent

```python
assert device.controllableName=="zwave:OnOffLightZWaveComponent
"
device.exec("off") #swith off the light
device.exec("on") #switch on the light
device.exec("onWithTimer", paramToDiscover) #switch on with a timer
```

#### Get all available commands for an device
````python
device = home.devices[0] #Let's take the first device
print(device.commands)
```
