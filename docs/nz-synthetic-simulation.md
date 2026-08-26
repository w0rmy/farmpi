# New Zealand synthetic simulation

The simulator is a realistic technical medium for training and usability evaluation, not an agronomic model, forecast, or farm recommendation engine. It runs wholly on the ESP32; FarmPi only receives `simulated=true` telemetry and applies the same validation/storage contract that future physical sensors will use.

The default profile is Waikato/Hamilton (`-37.7870`, `175.2793`, `Pacific/Auckland`). The firmware contains compact monthly daily low/high air-temperature baselines, adapted for a Waikato/Hamilton profile from [NIWA Hamilton station climate statistics](https://data.niwa.co.nz/products/climate-station-statistics/files/675f6de647ec2f9a228283b9); no runtime web request is made. The solar calculation uses latitude, longitude, date and Auckland daylight-saving rules to produce seasonal sunrise/sunset and daylight. Light is zero overnight, follows the daylight arc, and is attenuated by cloud/rain.

Air temperature reaches a minimum around sunrise and maximum in mid-afternoon; cloud/rain suppress daytime warming. Soil temperature is a slower, lagged state. Shared rain/cloud/pressure/wind weather is combined with persistent paddock differences in moisture, shade, temperature, pH, EC and pasture. Rain raises moisture, humidity and leaf wetness; moisture decays slowly when dry; occasional pasture drops represent grazing/cutting. There are no fabricated N/P/K fields—EC remains the raw chemistry proxy.

Sixteen virtual paddocks post evenly over one five-minute round (18.75 seconds apart). Persistent world state advances only before Paddock A, once per complete round, never once per POST. Real synchronized time determines the diurnal and seasonal shape.
