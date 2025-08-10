# PyCync
PyCync is a Python API library for interfacing with Cync smart devices.  

The goal of this project is to make a generalized Cync library that will eventually span the gamut of Cync devices and features, while breaking the underlying protocol into more concrete implementations.

## Disclaimers
This library is still an early work in progress. As such, various devices and features may not yet be supported. However, work is ongoing to add features to get the library closer to feature parity with the app.

The code has only been physically tested with Cync full color light bulbs and the dynamic effects LED strip, as those are the only light devices I own.  
If you encounter issues with a specific device, I can do my best to fix them, but there may be a delay if I need to purchase the device to test with.  

Currently, only Wi-Fi connected devices are supported. This means that you must have at least one Wi-Fi connected device in your home to utilize the library.  
Note that if you have a Wi-Fi connected device that acts as a bridge for other Bluetooth-only devices that communicate via Bluetooth mesh, all of the devices should work.  
Direct Bluetooth connections may be supported in the future, however at the moment it isn't a prioritized feature.

This library and its developers are in no way affiliated with GE Lighting or Savant Technologies. All APIs and protocols utilized in the library were created from reverse engineering.

# Using the Library
## Authenticating

1. The first step is to create an Auth object, which will handle authenticating your Cync user.
```
cync_auth = Auth(
                <an aiohttp Client Session>,
                username=your_email,
                password=your_password,
            )
```

2. Attempt to log in using the passed in credentials. If successful without two factor, the function will return your User object containing your auth token.
If two factor is required, the function will raise a TwoFactorRequiredError, and a two factor code will be emailed to your account at the time of the exception being raised.
```
try:
    user = cync_auth.login()
catch TwoFactorRequiredError:
    # Handle Two Factor
```

3. If a two factor code was required, you may call the same login function, and this time provide your two factor code.
```
try:
    user = cync_auth.login("123456")
catch AuthFailedError:
    # Handle Auth failure
```

4. After you have logged in, you may create a new Cync object and provide your Auth object.
```
cync_api = Cync.create(cync_auth)
```

## Getting Your Devices
There are two formats you can fetch your account's devices in.  

The first is a flattened view, where all of your account's devices are in a single-level list.  
This is useful if you want a simple view of all of your account's devices at once.
```
my_devices = cync_api.get_devices()
```

The second is a hierarchical format, with your devices organized into homes, rooms, and groups. It will return a list of homes, which each contain rooms, and then groups.  
This is useful if you would like to view your setup in a format that more closely matches the Cync app's categorization.
```
my_homes = cync_api.get_homes()
```
From here, you can filter devices as desired, and use the functions on the CyncDevice objects to control them.

## Setting a State Change Callback
If you would like to specify a callback function to run whenever device states change, you may provide one to the Cync object.  
The update_data parameter is a JSON object. The key is the device ID, and the value is the CyncDevice object with its new state set.  
The callback function may be either synchronous or asynchronous.
```
def my_callback(update_data: dict[int, CyncDevice]):
    # Handle updated data
    
cync_api.set_update_callback(my_callback)
```

## Other Things to Note
Only one connection can be established to the Cync server at a time per account.  
This means that if you are using the library, and then you open the Cync app on your phone, your library's connection will be closed.  
The server is the one that closes the connection, so unfortunately there is no getting around this. The library will attempt to reestablish the connection after 10 seconds.  
However, also note that once the library reestablishes the connection, your Cync app's connection will be closed. Love it.

# Thanks
A special thanks to [nikshriv](https://github.com/nikshriv)'s cync_lights project (https://github.com/nikshriv/cync_lights), and  
[unixpickle](https://github.com/unixpickle)'s cbyge project (https://github.com/unixpickle/cbyge).  

These projects and the discussions within them helped kickstart the direction to take for reverse engineering the Cync protocols.
