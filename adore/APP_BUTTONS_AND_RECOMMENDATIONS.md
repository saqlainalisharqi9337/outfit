# Adore — button actions and recommendation system

Documentation of the Flutter app as it works now. This covers every user-facing button and the outfit recommendation behaviour already built. It does not describe unfinished research training.

App name: Adore (Smart Cloth Advisor and Outfit Recommender).

Bottom navigation, left to right:

1. Home
2. Calendar
3. Wardrobe
4. Shop
5. Profile

Outfit suggestions are not a tab. They open from Home, from an event, or from the describe box on the Outfit screen.

---

## 1. Buttons and what they do

### Welcome and sign-in

| Button | What it does |
| --- | --- |
| Create Account | Opens the registration form. |
| Sign In | Shows the email and password form. |
| Continue as guest | Opens the app with the local demo profile. Does not call Supabase. |
| Back | Returns from the sign-in form to the welcome card. |
| Forgot password? | Opens the reset screen. |
| Sign In (form) | Signs in with the typed email and password. The demo email and password open the local demo instead. |

### Create account

| Button | What it does |
| --- | --- |
| Register | Creates the account on Supabase, then saves the profile. |
| Use demo profile instead | Opens the local demo profile without creating an account. |

### Forgot password

| Button | What it does |
| --- | --- |
| Send reset link | For the demo account, shows the demo password on screen. For any other email, asks Supabase to send a reset email. |

### First-time profile setup

| Button | What it does |
| --- | --- |
| Continue | Moves to the next setup step (gender, body, culture, style, location). |
| Finish | Saves the setup on the last step and enters the app. |
| Back | Returns to the previous setup step. |
| Add photo | Lets the user pick a profile photo during setup. |
| Use my location | Requests GPS and fills the city from the device location. |

### Home

| Button | What it does |
| --- | --- |
| Wardrobe icon (top left) | Switches to the Wardrobe tab. |
| Notifications | Opens a short notice that a new outfit can be generated. Close dismisses it. |
| Profile icon | Switches to the Profile tab. |
| Get Outfit Suggestions | Opens the Outfit screen and generates looks from the wardrobe and today’s weather. |
| Use live location | Uses GPS to load weather for the current city. Shown when weather is missing. |
| Choose country & city | Opens the manual city picker. Shown when weather is missing. |
| Refresh (on the weather card) | Reloads weather for the selected city and refreshes the outfit. |
| Location edit (on the weather card) | Opens the city picker. |
| GPS (on the weather card) | Uses the phone location for weather. |
| See all | Opens the Outfit screen. |
| Recommend outfit | Generates an outfit when none is showing yet. |
| Try again | Retries generation after an error. |
| Today’s outfit card | Opens the Outfit screen. |
| Adorable | Switches to the Wardrobe tab. |
| Calendar | Switches to the Calendar tab. |
| Trends | Opens the trends list. |
| Shop | Switches to the Shop tab. |
| An upcoming event row | Opens that event’s detail page. |

### Outfit suggestions

| Button | What it does |
| --- | --- |
| Go | Reads the description (for example “outfit for marriage”), extracts the event type, and generates outfits. |
| Your wardrobe is empty — add clothes | Switches to the Wardrobe tab. |
| An outfit card | Opens the outfit detail. |
| View product | Opens the shop product suggested for a missing wardrobe piece. |
| Like | Saves a positive vote for this outfit. Later recommendations prefer similar pieces. |
| Dislike | Saves a negative vote. Later recommendations avoid similar pieces. |
| Save | Stores the outfit in the user’s saved looks. |
| Share | Shares the outfit title and reasons through the phone share sheet. |
| Add missing item to cart | Puts the first suggested shop product into the cart. |

### Calendar and events

| Button | What it does |
| --- | --- |
| A day on the calendar | Shows events for that day. |
| An event row | Opens the event detail. |
| Add event | Opens the new-event form. |
| Date and time row | Opens the date picker, then the time picker. |
| Save event | Checks the name and city, looks up weather for that city and date when a forecast exists, and saves the event. |
| Edit (pencil) | Opens the same form with the saved name, date, city, occasion, and description. |
| Recommend outfit for this event | Uses the event type, description, city, and that date’s forecast, then opens the Outfit screen. |
| Delete event | Removes the event and returns to the calendar. |

### Wardrobe

| Button | What it does |
| --- | --- |
| Add a clothing photo / Add cupboard photo | Opens the add-clothing page. |
| A clothing photo | Opens that item’s detail page. |
| Camera | Takes a new photo of a garment. |
| Gallery | Picks an existing photo. |
| Retake | Takes another photo. |
| Analyze with AI | Sends the photo to the clothing service and fills category, type, and color. |
| A detected chip | Applies that detected type to the form. The X removes a wrong detection. |
| Save to cupboard | Uploads the photo and stores the item on the account. |
| Delete (on a clothing detail) | Asks for confirmation, then removes the item. |
| Cancel (delete dialog) | Closes the dialog and keeps the item. |

### Shop

| Button | What it does |
| --- | --- |
| Cart icon | Opens the cart. |
| A product card | Opens the product page. |
| Add to cart | Adds that product to the cart. |
| Minus / plus | Changes the quantity of a cart line. |
| Checkout | Opens the demo checkout page. |
| Place demo order | Saves the order and clears the cart. No real payment is taken. |
| Done / back from confirmation | Returns toward the shop. |

### Profile

| Button | What it does |
| --- | --- |
| Inbox icon | Opens inbox and FAQ. |
| Profile photo | Uploads a new avatar. |
| Edit Profile | Edits the display name. Email stays read-only. |
| Body type | Saves a body type on the account (rectangle, pear, inverted triangle, hourglass, apple). |
| Size | Saves clothing size and bra size in the existing profile preferences. |
| Dark / light switch | Changes the theme for the whole app and keeps it on the device. |
| Outfit History | Lists past likes, dislikes, and saves. |
| Favourite Style | Lets the user pick style preferences used by recommendations. |
| More Recommendation | Opens the full preference editor (culture, body, skin tone, colors, modest dressing). |
| Your Orders | Opens the order list. The badge is the real order count. |
| Help | Opens the support notes. |
| Log out | Signs out of the account or leaves demo mode. |
| Delete Account | Explains that the app does not delete the Supabase user. It does not remove the account. |

### Other

| Button | What it does |
| --- | --- |
| Try again (error banners) | Repeats the failed load. |
| Close (image viewer) | Closes a full-screen photo. |

---

## 2. Recommendations already built

The outfit engine is rule-based scoring. It does not train a new model when the user asks for an outfit. Image recognition is a separate service. This section is only the outfit ranker.

### What a recommendation uses

- The signed-in profile: gender, culture, body type, skin tone, favorite colors, preferred styles, preferred occasions, excluded types, excluded styles, and modest dressing.
- Clothes already in the wardrobe. Owned clothes are ranked first.
- Today’s weather on Home and on the Outfit screen: temperature, condition, rain, and the weather band (very cold, cold, mild, hot).
- An event, when the user starts from Calendar: selected occasion, description, city, and the forecast for that event date.
- A typed description on the Outfit screen. Clear words set the occasion. Examples: marriage or wedding, office or meeting, hiking, romantic dinner, party, gym, religious events.
- If the description does not name an event, the selected occasion or the profile default is kept. The app does not invent an occasion.
- Past Like, Dislike, and Save votes.
- Shop products, used only when the wardrobe has no suitable piece.
- Trends loaded for that user.

### How an outfit is chosen

1. Drop clothes that conflict with gender, modest rules, excluded types or styles, the occasion, or the weather. Hot weather does not keep heavy coats unless the user explicitly asked for a jacket or layer. Cold weather can add an outer layer.
2. Score the remaining wardrobe items for weather, culture, occasion, color and skin tone, personal preference, wardrobe ownership, and body type.
3. Build complete outfits from those scores.
4. If the wardrobe is empty or every item was filtered out, suggest shop products instead and mark the result as not from the wardrobe.
5. Show a score breakdown and short reasons (“Why we recommend this”).

### Occasions the engine knows

Casual day out, university, office, formal event, wedding, party, date, sports, travel, religious event, outdoor activity, and other.

Description words that map onto those occasions include wedding, marriage, nikah, shaadi, walima, mehndi, office, meeting, interview, business, gym, hiking, beach, travel, date night, romantic dinner, party, formal, mosque or eid, and family gathering.

### Event weather

For a saved event, the city the user typed is geocoded without GPS. The forecast is requested for that calendar date, not for today. Temperature, condition, humidity, and wind are used when the weather service returns them. Dates in the past, or more than 15 days ahead, do not get a made-up temperature. The event can still be saved. A recommendation for that event waits until a real forecast exists.

### What the user sees on an outfit

- Whether the look is from the wardrobe or from new shop suggestions.
- Each slot: top, bottom, shoes, outer layer, or accessory, with color and formality.
- Match percent and bars for weather, culture, occasion, color and skin tone, preference, wardrobe, and body type.
- Like, Dislike, Save, and Share.
- A shop link when a required piece is missing.

### What this system does not do

- It does not charge a payment card. Checkout is a stored demo order.
- It does not delete a Supabase account from the Delete Account button.
- It does not use Mask R-CNN for live clothing photos. Live clothing classification is the existing MobileNetV2 path. That is separate from outfit ranking.
