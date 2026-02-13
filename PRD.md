# Refin Listing Data Post Processing

## Objective
Process the raw data uploaded to the table `staging_redfin_listings` and turn it into clean data, as well as derive new features to be used in modeling.

## Tasks
Completely redesign the current DAG for processing the staging table data. Each item below lists the table the data will go into and each bullet lists the field in the table. Each bullet contains the new table column name, a description of the field, the field type, and how to parse the data from the staging table.

1. Create records in table `redfin_listings`
- [ ] `id`
    description: "The property ID (unique)"
    type: [PK] integer
- [ ] `street_address`
    description: "The street address of the property"
    type: str
    values:
        - parse `address` and strip city, state, and zipcode
- [ ] `city`
    description: "The address city"
    type: str
    values:
        - use `city`
- [ ] `state`
    description: "The address state"
    type: str
    values:
        - use `state`
- [ ] `zip_code`
    description: "The address zipcode"
    type: str
    values:
        - use `zip_code`
- [ ] `listing_status`
    description: "The status of the listing"
    type: str
    values:
        - use `listing_status` and standardize into the following values:
            - SOLD
            - CONTINGENT
            - PENDING
            - COMING SOON
            - FOR SALE
            - FOR RENT
            - UNDER CONTRACT
- [ ] `sold_date`
    description: "The date the property was last sold"
    type: date
    values:
        - parse `sold_date`
        - If just includes a month assume it was sold on the first day of the month
- [ ] `sold_price`
    description: "The value the property was last sold at"
    type: float
    values:
        - parse `sold_price`
        - None if no value
- [ ] `listing_price`
    description: "The listing price"
    type: float
    values:
        - parse `listing_price`
        - None if no value
- [ ] `description`
    description: "The listing description"
    type: str
    values:
        - use `description` no transform needed
- [ ] `flood_factor`
    description: "The climate flood factor"
    type: category
    values:
        - use `climate_flood_factor` and map to these values:
            - 1: Minimal
            - 2: Minor
            - 3: Moderate
            - 4: Major
            - 5: Severe
            - 6: Extreme
- [ ] `fire_factor`
    description: "The climate fire factor"
    type: category
    values:
        - use `climate_fire_factor` and map to these values:
            - 1: Minimal
            - 2: Minor
            - 3: Moderate
            - 4: Major
            - 5: Severe
            - 6: Extreme
- [ ] `has_garage`
    description: "Indicates whether the property has a garage"
    type: bool
    values:
        - True if `property_details.garage` == "Yes"
        - False otherwise
- [ ] `num_garage_spaces`
    description: "The number of parking spaces in the garage"
    type: int
    values:
        - parse `property_details.garage_spaces`, 0 if missing
- [ ] `parking_type`
    description: "Provides context on the type of parking"
    type: category
    values:
        in order of presidence:
        - "Attached Garage" if `property_details.attached_garage`=="Yes" or "Attached" in `property_details.parking_features`
        - "Detached Garage" if "Detached" in `property_details.parking_features`
        - "Carport" if "Carport" or "Covered" in `property_details.parking_features`
        - "Street" if "On Street" in `property_details.parking_features`
        - "Garage" if `property_details.garage`=="Yes"
        - None otherwise
- [ ] `garage_entry`
    description: "Provides context about the orientation of the garage"
    type: category
    values:
        in order of presidence:
        - "Front" if "Garage Faces Front" in `property_details.parking_features`
        - "Side" if "Garage Faces Side" in `property_details.parking_features`
        - "Rear" if "Garage Faces Rear" in `property_details.parking_features`
        - None otherwise
- [ ] `driveway_surface`
    description: "Provides context about quality of the driveway"
    type: category
    values:
        in order of presidence:
        - "Paved" if `property_details.parking_features` contains ["Concrete","Parking Pad","Paved","Asphalt","Paver Block","Brick","Paver"]
        - "Unpaved" if `property_details.parking_features` contains ["Gravel","Unpaved","Dirt","Crushed Stone", "Stone"]
        - None otherwise
- [ ] `has_workshop`
    description: "Indicates whether the preoprty has a workshop"
    type: bool
    values:
        - True if `property_details.parking_features` contains "Workshop in Garage"
        - True if `property_details.other_structures` contains ["Workshop"]
        - False otherwise
- [ ] `has_circular_driveway`
    description: "Indicates whether the driveway is circular"
    type: bool
    values:
        - True if `property_details.parking_features` contains "Circular Driveway"
        - False otherwise
- [ ] `has_ev_charging`
    description: "Indicates whether the parking area has EV charging"
    type: bool
    values:
        - True if `property_details.parking_features` contains "Electric Vehicle Charging Station(s)"
        - False otherwise
- [ ] `has_fireplace`
    description: "Indicates whether the property has a fireplace"
    type: bool
    values:
        - True if `property_details.fireplace` == "Yes"
        - False otherwise
- [ ] `water_heater_energy_source`
    description: "The energy source for the water heater (e.g., Gas, Electric)"
    type: category
    values:
        in order of presidence:
        - "Gas" if "Gas Water Heater" or "Propane Water Heater" in `property_details.appliances`
        - "Electric" if "Electric Water Heater" in `property_details.appliances`
        - "Solar" if "Solar Hot Water" in `property_details.appliances`
        - "UNKNOWN" otherwise
- [ ] `cooktop_energy_source`
    description: "The energy source for the cooktop (e.g., Gas, Electric)"
    type: category
    values:
        in order of presidence:
        - "Gas" if "Gas Cooktop" or "Gas Range" or "Built-In Gas Range" or "Free-Standing Gas Range" "Propane Cooktop" in `property_details.appliances`
        - "Electric" if "Electric Range" or "Electric Cooktop" or "Free-Standing Electric Range" or "Induction Cooktop" or "Built-In Electric Range" in `property_details.appliances`
- [ ] `oven_energy_source`
    description: "The energy source for the oven (e.g., Gas, Electric)"
    type: category
    values:
        in order of presidence:
        - "Gas" if "Gas Oven" or "Free-Standing Gas Oven"  in `property_details.appliances`
        - "Electric" if "Electric Oven" or "Built-In Electric Oven" or "Built-In Gas Oven" or "Free-Standing Electric Oven" in `property_details.appliances`
        - "UNKNOWN" otherwise
- [ ] `has_drink_fridge`
    description: "Indicates whether the property has a wine or beverage fridge"
    type: bool
    values:
        - True if `property_details.appliances` contains ["Bar Fridge","Wine Refrigerator","Wine Cooler"]
        - False otherwise
- [ ] `has_stainless_appliances`
    description: "Indicates whether the property has stainless steel appliances"
    type: bool
    values:
        - True if `property_details.appliances` contains ["Stainless Steel Appliance(s)"]
        - False otherwise
- [ ] `appliances_included_count`
    description: "Number of appliances that convey with the property. Ranges from 0-3 (fridge, washer, dryer)"
    type: bool
    values:
        - +1 if `property_details.appliances` contains any of ["Refrigerator","Free-Standing Refrigerator","Built-In Refrigerator",]
        - +1 if `property_details.appliances` contains any of ["Washer","Washer/Dryer","Washer/Dryer Stacked","ENERGY STAR Qualified Washer",]
        - +1 if `property_details.appliances` contains any of ["Dryer","Washer/Dryer","Washer/Dryer Stacked","ENERGY STAR Qualified Dryer"]
- [ ] `has_efficient_windows`
    description: "Indicates whether the property has updated windows"
    type: bool
    values:
        - True if `property_details.window_features` contains ["Insulated Windows","Double Pane Windows","Low-Emissivity Windows","ENERGY STAR Qualified Windows","Triple Pane Windows"]
        - False otherwise
- [ ] `has_skylights`
    description: "Indicates whether the property has skylights"
    type: bool
    values:
        - True if `property_details.window_features` contains ["Skylight",]
        - False otherwise
- [ ] `has_bay_window`
    description: "Indicates whether the property has bay windows"
    type: bool
    values:
        - True if `property_details.window_features` contains ["Bay","Garden"]
        - False otherwise
- [ ] `laundry_location`
    description: "Where the laundry is located in the house"
    type: category
    values:
        in order of presidence:
        - "Upper" if "Upper" in `property_details.laundry_features`
        - "Main" if "Main" in `property_details.laundry_features`
        - "Basement" if "Lower" or "Basement"  in `property_details.laundry_features`
        - "Garage/Out" if "Garage" or "Outside"  in `property_details.laundry_features`
        - "Standard" otherwise
- [ ] `has_laundry_room`
    description: "Indicates whether the property has a dedicated laundry room"
    type: bool
    values:
        - True if `property_details.laundry_features` contains ["Laundry Room",]
        - False otherwise
- [ ] `has_utility_sink`
    description: "Indicates whether the property has a utility sink"
    type: bool
    values:
        - True if `property_details.laundry_features` contains ["Sink",]
        - False otherwise
- [ ] `countertop_material`
    description: "The material the countertop is made from"
    type: category
    values:
        in order of presidence:
        - "Ultra" if "Quartz Counters" in `property_details.interior_features`
        - "Premium" if "Granite Counters" or "Stone Counters" in `property_details.interior_features`
        - "Standard" if "Tile Counters" or "Laminate Counters"  in `property_details.interior_features`
        - "Unknown" otherwise
- [ ] `is_primary_downstairs`
    description: "Indicates whether the primary bedroom is on the first floor"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["Primary Downstairs",]
        - False otherwise
- [ ] `has_guest_suite`
    description: "Indicates whether the home has a guest suite for in laws"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["In-Law Floorplan", "Second Primary Bedroom", "Apartment/Suite, Room Over Garage"]
        - False otherwise
- [ ] `has_butler_pantry`
    description: "Indicates whether the home has a butlers pantry"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["Butler's Pantry"]
        - False otherwise
- [ ] `has_walkin_closets`
    description: "Indicates whether the home has walk in closets"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["Walk-In Closet(s)"]
        - False otherwise
- [ ] `has_tall_ceilings`
    description: "Indicates whether the home has high ceilings"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["High Ceilings","Vaulted Ceiling(s)","Cathedral Ceiling(s)",]
        - False otherwise
- [ ] `has_luxury_ceilings`
    description: "Indicates whether the home has luxury ceilings"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["Tray Ceiling(s)","Coffered Ceiling(s)","Beamed Ceilings",]
        - False otherwise
- [ ] `has_sauna`
    description: "Indicates whether the home has a sauna"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["Sauna",]
        - False otherwise
- [ ] `has_bar`
    description: "Indicates whether the home has a bar"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["Bar",]
        - False otherwise
- [ ] `has_second_primary`
    description: "Indicates whether the home has a second primary bedroom"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["Second Primary Bedroom",]
        - False otherwise
- [ ] `has_room_over_garage`
    description: "Indicates whether the home has a room above the garage"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["Room Over Garage",]
        - False otherwise
- [ ] `has_open_floorplan`
    description: "Indicates whether the home has a room above the garage"
    type: bool
    values:
        - True if `property_details.interior_features` contains ["Open Floorplane",]
        - False otherwise
- [ ] `has_outdoor_fireplace`
    description: "Indicates whether the home has an outdoor fireplace"
    type: bool
    values:
        - True if `property_details.fireplace_features` contains ["Outside","Fire Pit",]
        - False otherwise
- [ ] `has_primary_fireplace`
    description: "Indicates whether the home has a fireplace in the primary bedroom/bath"
    type: bool
    values:
        - True if `property_details.fireplace_features` contains ["Primary Bedroom","Bedroom","Bath",]
        - False otherwise
- [ ] `has_architectural_fireplace`
    description: "Indicates whether the home has an architectural fireplace"
    type: bool
    values:
        - True if `property_details.fireplace_features` contains ["Double Sided","See Through",]
        - False otherwise
- [ ] `fireplace_fuel_source`
    description: "The fuel used for the fireplace"
    type: category
    values:
        in order of presidence:
        - "Gas" if "Gas Log" or "Gas" or "Sealed Combustion" or "Propane" in `property_details.fireplace_features`
        - "Wood" if "Wood Burning" or "Masonry" or "Wood Burning Stove" in `property_details.fireplace_features`
        - "Electric" if "Electric" in `property_details.fireplace_features`
        - "Unknown" otherwise
- [ ] `num_fireplaces`
    description: "The number of fireplaces"
    type: int
    values:
        - parse `property_details.fireplaces_total`, 0 if missing
- [ ] `is_carpet_free`
    description: "Indicates whether the home has no carpet"
    type: bool
    values:
        - True if `property_details.flooring` does not contain ["Carpet"]
        - False otherwise
- [ ] `has_premium_stone`
    description: "Indicates whether the home has premium stone"
    type: bool
    values:
        - True if `property_details.flooring` does not contain ["Marble","Slate","Granite","Stone",]
        - False otherwise
- [ ] `has_hardwood`
    description: "Indicates whether the home has real hardwood"
    type: bool
    values:
        - True if `property_details.flooring` does not contain ["Wood","Bamboo","Parquet","Cork","FSC or SFI Certified Source Hardwood"]
        - False otherwise
- [ ] `has_crawl_space`
    description: "Indicates whether the home has a crawlspace"
    type: bool
    values:
        - True if `property_details.crawl_space` =="Yes"
        - False otherwise
- [ ] `facade_type`
    description: "The material used for the facade"
    type: category
    values:
        in order of presidence:
        - "Masonry" if `property_details.construction_materials` contains ["Brick","Stone","Stucco","Block","Plaster",]
        - "Fiber Cement" if `property_details.construction_materials` contains ["Fiber Cement","HardiPlank","Cement"]
        - "Synthetic" if `property_details.construction_materials` contains ["Vinyl","Metal","Aluminum",]
        - "Wood" if `property_details.construction_materials` contains ["Masonite","Wood","Cedar","Shake","Log","Board & Batten Siding","Lap Siding"]
        - None otherwise
- [ ] `building_area`
    description: "The total building area in sqft"
    type: float
    values:
        - parse `property_details.building_area_total`, 0 if missing
- [ ] `above_grade_finished_area`
    description: "The total finished building area above grade in sqft"
    type: float
    values:
        - parse `property_details.above_grade_finished_area`, 0 if missing
- [ ] `below_grade_finished_area`
    description: "The total finished building area below grade in sqft"
    type: float
    values:
        - parse `property_details.below_grade_finished_area`, 0 if missing
- [ ] `num_stories`
    description: "The number of building levels"
    type: category
    values:
        in order of presidence:
        - parse `property_details.stories`
        - If null then parse `property_details.levels` and map these values:
            Two
            Three Or More
            One and One Half
            One
            Tri-Level
            Multi/Split
            Bi-Level
            Three
        - None if missing
- [ ] `lot_size`
    description: "The lot size in acres"
    type: float
    values:
        - parse `property_details.lot_size_acres`
        - if missing parse `property_details.lot_size`
        - if missing parse `property_details.lot_size_square_feet`
        - if thats missing parse `property_details.lot_size_area` and `property_details.lot_size_units`
        - None otherwise
- [ ] `is_waterfront`
    description: "Indicates whether the home is waterfront"
    type: bool
    values:
        - True if `property_details.waterfront` =="Yes"
        - True if `property_details.features` contains ["Waterfront"]
        - False otherwise      
- [ ] `buyer_financing`
    description: "The type of financing the buyer used"
    type: category
    values:
        - use `property_details.buyer_financing`
- [ ] `is_septic`
    description: "Indicates whether the home is on a septic tank"
    type: bool
    values:
        - True if `property_details.sewer` contains ["Septic","Private Sewer",]
        - False otherwise  
- [ ] `is_well_water`
    description: "Indicates whether the home uses well water"
    type: bool
    values:
        - True if `property_details.water_source` contains ["Well","Private",]
        - False otherwise  
- [ ] `no_heating`
    description: "Indicates whether the home is not heated"
    type: bool
    values:
        - True if `property_details.heating` =="No"
        - False otherwise 
- [ ] `no_cooling`
    description: "Indicates whether the home is not cooled"
    type: bool
    values:
        - True if `property_details.cooling` =="No"
        - False otherwise 
- [ ] `has_hoa`
    description: "Indicates whether the home is in an HOA"
    type: bool
    values:
        - True if `property_details.association` =="Yes"
        - False otherwise 
- [ ] `has_enclosed_porch`
    description: "Indicates whether the home has an enclosed porch"
    type: bool
    values:
        - True if `property_details.patio_and_porch_features` contains ["Screened","Enclosed","]
        - False otherwise 
- [ ] `has_front_porch`
    description: "Indicates whether the home has a front porch"
    type: bool
    values:
        - True if `property_details.patio_and_porch_features` contains ["Front Porch","Wrap Around","]
        - False otherwise 
- [ ] `has_fenced_yard`
    description: "Indicates whether the home has a fenced yard"
    type: bool
    values:
        In order of presidence:
        - True if `property_details.fencing` contains a value and does not contain ["None","Invisible","Partial","Electric"]
        - True if `property_details.exterior_features` contains ["Fence","Private Yard","Dog Run"]
        - False otherwise 
- [ ] `has_outdoor_kitchen`
    description: "Indicates whether the home has an outdoor kitchen"
    type: bool
    values:
        - True if `property_details.exterior_features` contains ["Kitchen","Built-in Barbecue","Gas Grill"]
        - True if `property_details.other_structures` contains ["Outdoor Kitchen"]
        - False otherwise 
- [ ] `has_sport_court`
    description: "Indicates whether the home has an outdoor court (e.g., tennis, basketball)"
    type: bool
    values:
        - True if `property_details.exterior_features` contains ["Tennis Court(s)","Basketball Court","Arena"]
        - False otherwise 
- [ ] `has_private_pool`
    description: "Indicates whether the home has a private pool"
    type: bool
    values:
        in order of presidence:
        - True if `property_details.exterior_features` contains ["Pool"]
        - True if `property_details.features` contains ["Pool"]
        - True if `property_details.pool_features` contains a value and does not contain ["Swimming Pool Com/Fee","Community","Association","None"]
        - False otherwise
- [ ] `has_community_pool`
    description: "Indicates whether the home has a community pool"
    type: bool
    values:
        in order of presidence:
        - True if `property_details.community_features` contains ["Pool"]
        - True if `property_details.pool_features` contains ["Swimming Pool Com/Fee","Community","Association"]
        - True if `property_details.association_amenities` contains ["Pool",]
        - False otherwise
- [ ] `has_clubhouse`
    description: "Indicates whether the home has a community clubhouse"
    type: bool
    values:
        - True if `property_details.community_features` contains ["Clubhouse"]
        - True if `property_details.association_amenities` contains ["Clubhouse","Recreation Facilities","Fitness Center",]
        - False otherwise 
- [ ] `has_exterior_storage`
    description: "Indicates whether the home has a exterior storage building"
    type: bool
    values:
        in order of presidence:
        - True if `property_details.other_structures` contains ["Shed","Storage","Workshop","Outbuilding","Barn","Second Garage",]
        - True if `property_details.exterior_features` contains ["Storage","Barn","Equestrian Facilities","Outbuilding","Shed","Stable"]
        - False otherwise 
- [ ] `has_garden`
    description: "Indicates whether the home has a garden/greenhouse"
    type: bool
    values:
        - True if `property_details.exterior_features` contains ["Garden","Greenhouse"]
        - True if `property_details.other_structures` contains ["Greenhouse"]
        - False otherwise 
- [ ] `association_fee`
    description: "The yearly HOA fee"
    type: float
    values:
        - parse `property_details.association_fee` and `property_details.association_fee_frequency`, convert to a yearly value
        - parse `property_details.association_fee_2` and `property_details.association_fee_2_frequency`, convert to a yearly value
        - parse `property_details.hoa_dues` and convert to a yearly value
        - sum the two fees
- [ ] `location`
    description: "The coordinates of the house"
    type: geometry
    values:
        - parse latitude from `property_details.latitude`
        - parse longitude from `property_details.longitude`
        - if the above are empty use the geocoding service using the `address` field 
- [ ] `year_built`
    description: "The year the home was built"
    type: int
    values:
        in order of presidence:
        - use `year_built`
        - If null then parse `property_details.year_built`
        - None otherwise
- [ ] `num_beds`
    description: "The number of bedrooms"
    type: int
    values:
        in order of presidence:
        - use `beds`
        - If null then parse `property_details.beds`
        - if null then parse `property_details.num_of_bedrooms`,
        - None otherwise
- [ ] `num_baths`
    description: "The number of bathrooms"
    type: float
    values:
        in order of presidence:
        - use `baths`
        - If null then parse `property_details.baths`
        - If null then parse and add `property_details.num_of_full_bathrooms` and `property_details.num_of_half_bathrooms`
        - None otherwise
- [ ] `sqft`
    description: "The sqft of the house"
    type: int
    values:
        in order of presidence:
        - use `sqft`
        - If null then parse `property_details.year_built`
        - If null then parse `property_details.living_area`
        - None otherwise
- [ ] `price_per_sqft`
    description: "The listing price per sqft of the house"
    type: float
    values:
        in order of presidence:
        - use `price_per_sqft`
        - If null then calculate it from taking the calculated features `listing_price` / `sqft`
        - None otherwise
- [ ] `listing_agent`
    description: "The listing agent for the house"
    type: str
    values:
        - use `listing_agent`, no transform needed
- [ ] `listing_brokerage`
    description: "The listing broker for the house"
    type: str
    values:
        - use `listing_brokerage`, no transform needed
- [ ] `buying_agent`
    description: "The buying agent for the house"
    type: str
    values:
        - use `buying_agent`, no transform needed
- [ ] `buying_brokerage`
    description: "The buying broker for the house"
    type: str
    values:
        - use `buying_brokerage`, no transform needed
- [ ] `hoa_name`
    description: "The name of the HOA"
    type: str
    values:
        - use `property_details.association_name`, no transform needed
- [ ] `year_renovated`
    description: "The year the house was last renovated"
    type: int
    values:
        - parse `property_details.year_renovated`
- [ ] `apn`
    description: "The APN identifier of the house"
    type: str
    values:
        - parse `property_details.apn`
        - should be in the format "0761.03 34 2215 000"
        - some cases it appears like "0763593132" can this be parsed?
        - sometimes says "See Plat" - just use None for these and others
- [ ] `contract_date`
    description: "The date the contract status changed"
    type: date
    values:
        - parse `property_details.contract_status_change_date`
- [ ] `num_parking_spaces`
    description: "The number of parking spaces"
    type: int
    values:
        in order of presidence:
        - parse `property_details.parking_total`
        - parse `property_details.parking_spaces`
- [ ] `has_garden`
    description: "Indicates whether the home has a garden/greenhouse"
    type: bool
    values:
        - True if `property_details.exterior_features` contains ["Garden","Greenhouse"]
        - True if `property_details.other_structures` contains ["Greenhouse"]
        - False otherwise 
- [ ] `property_photos`
    description: "The S3 location of the property photos"
    type: list[str]
    values:
        - use `photo_s3_paths`
- [ ] `source_file`
    description: "The name of the source HTML file"
    type: str
    values:
        - use `source_file`
- [ ] `processed_at`
    description: "The time the record was processed"
    type: datetime
    values:
        - set to current datetime

2. Create records in table `sale_history`
Parse each record in `sale_history` column into these columns
- [ ] `id`
    description: "The event ID (unique)"
    type: [PK] integer
- [ ] `property_id`
    description: "Link to the property ID"
    type: [FK] integer
- [ ] `date`
    description: "The date of the sale event"
    type: date
    values:
        - parse `date`
- [ ] `event`
    description: "The type of sale event"
    type: str
    values:
        - use `event`, standardize in all caps
- [ ] `price`
    description: "The event price"
    type: float
    values:
        - parse `price`
- [ ] `source`
    description: "The event source"
    type: str
    values:
        - set to "Redfin"

3. Create records in table `tax_history`
Parse each record in `tax_history` column into these columns
- [ ] `id`
    description: "The event ID (unique)"
    type: [PK] integer
- [ ] `property_id`
    description: "Link to the property ID"
    type: [FK] integer
- [ ] `date`
    description: "The date of the tax event"
    type: date
    values:
        - parse `year` - set to 1st of the year
- [ ] `property_tax`
    description: "The tax amount"
    type: float
    values:
        - parse `tax`, only extract the tax amount not the % change
- [ ] `assessment_value_land`
    description: "The assessed land value"
    type: float
    values:
        - parse `land`
- [ ] `assessment_value_additions`
    description: "The assessed additions value"
    type: float
    values:
        - parse `additions`
- [ ] `assessment_value`
    description: "The total assessed value"
    type: float
    values:
        - parse `assessed_value`
- [ ] `source`
    description: "The event source"
    type: str
    values:
        - set to "Redfin"

4. Create records in table `property_valuations`
Keep the current processing logic. However, adjust the estimated_at column. Instead of using the processing time use the `loaded_at` value from `staging_redfin_listings`

5. Write tests for the above to verify that the values are being parsed correctly.
