# PRD

We need to make the following changes / improvements to the dashboard page of the app.

- [x] On the nuisance map card, make it more clear that one set of selectors is for noise levels and the other is for actual locations
- [x] The schools map should display the school district geometry where the property is located in, this can be retrieved from the tiger_school_district table
- [x] The landing page search bar has a bug. the suggested address dropdown doesnt fully lay overtop the tag text under the search bar so sometimes you click the background text and not the suggested result.
- [x] Sync the map themes across all tabs. for example, if the user selects street view on any given map, then when switching to a new tab the map should also be in street view. Configure this as something we can store in the users browser so it persists across page visits as well 
- [x] Remove the hardcoded nuisance cards and points on the map, it should display the data from the backend. if there are no results then indicate to the user no nuisances found
- [x] when expanding the listing photos, the other page cards should not show overtop of the photo
- [x] verify that the road, rail, and airport geometries are actually being pulled into the map. for example, i'm not seing any airport dots showing
- [x] on the schools tab, the school cards should display the driving and walking times.
- [x] on the greenspace tab, link the map to the backend. It should pull and display greenspaces and greenways on the map
- [x] on the greenspace tab, link the cards on the left to the map. it should display whatever places are currently visible in the map boundary.
- [x] I want to update the dashboard page to not prevent loading an address thats not in the database. It should still load the address and display empty data for items that need the listing data. but other charts can still be displayed (like the demographics tab). still have a dialouge somewhere that asks the user if they want to submit a request to load the data.
- [x] The property isnt in our database message on the dashboard page isnt displaying correctly. It should be under the breadcrumb. right now its overlapped and difficult to read.
- [x] When a property is not in the database, show a generic icon image for the listing photo instead of the empty image file. Also there shouldnt be an image carasoul in this case. Additionally, you shouldn't display for sale or days on the market labels. the cards that cant display data, like the valuation estimate, price history, and value drivers cards should have generic overlays that indicate this data isnt available and to request it.