## weather_provider
Provides weather informations for connected energy monitor locations.
Weather information could be used to determine expected plant output,
detect potential faults, or ensure the plant operates within expected
conditions. Weather information is source from OpenWeatherMap.

### configuration
The app (and container) can be configured through the following environmental variables:
- `OWM_API_KEY`: OpenWeatherMap API key (mandatory)
- `MQTT_BROKER`: address of the MQTT broker (defaults to 127.0.0.1)
- `MQTT_BROKER_PORT`: port of the MQTT broker (defaults to 1883)
- `MQTT_SUBSCRIBER_ID` = MQTT subscriber ID (defaults to enmon_weather)
- `REPORTING_INTERVAL` = weather reporting interval (defaults to 15 mins)

