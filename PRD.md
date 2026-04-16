# My App Idea

> How to use:
> 1. Copy this file: cp ~/PRD-TEMPLATE.md ~/PRD.md
> 2. Fill in each section below (delete the examples, write your own)
> 3. Tell Cline: "Read ~/PRD.md and build it"
> Cline will pick the best technologies and build everything for you.

---

## What is your app?

**App name**: [Give your app a name, e.g. "FoodBuddy"]

**Describe it in one sentence**: [e.g. "An app that suggests recipes based on ingredients I have at home"]

**Who will use it?**: [e.g. "Home cooks who want to reduce food waste"]

## What can users do?

List the main things a user can do in your app. Keep it to 3-5 items.

1. [e.g. Enter the ingredients I have in my fridge]
2. [e.g. See recipe suggestions that match my ingredients]
3. [e.g. Save my favorite recipes for later]
4. [e.g. Generate a shopping list for missing ingredients]

## What pages does the app have?

Describe each screen the user will see.

- **Home page**: [e.g. A search bar where I type my ingredients, with popular recipes below]
- **Results page**: [e.g. A grid of recipe cards showing photo, title, and cook time]
- **Recipe detail page**: [e.g. Full recipe with ingredients list, step-by-step instructions, and a save button]

## How should it look?

- Style: [e.g. Clean and modern / Colorful and fun / Dark and sleek / Simple and minimal]
- Colors: [e.g. Green and white / Blue theme / Dark mode / I don't mind, let Cline decide]
- Inspiration: [e.g. "Like Instagram but for recipes" / "Similar to Notion" / No preference]

## Does the app need to save data?

If your app needs to remember things (users, posts, scores, etc.), describe what:

- [e.g. User accounts with name and email]
- [e.g. Saved recipes per user]
- [e.g. Ingredient database with categories]

> If you skip this, Cline will use a simple file-based database.
> For Oracle Database, see ~/CLAUDE.md for connection details.

## Demo scenario

How would you show this app in a 1-2 minute demo?

1. [e.g. Open the app and see the landing page]
2. [e.g. Type "chicken, rice, garlic" in the search bar]
3. [e.g. Three matching recipes appear as cards]
4. [e.g. Click "Garlic Chicken Rice" to see the full recipe]
5. [e.g. Hit the save button and see it in my favorites]

---

## Complete Example

Here is a filled-in example for reference:

**App name**: StudyBuddy

**Describe it in one sentence**: A flashcard app that helps students study with spaced repetition

**Who will use it?**: University students preparing for exams

**What can users do?**
1. Create flashcard decks for different subjects
2. Study cards one at a time — flip to see the answer, rate how well I knew it
3. See my study streak and progress over time
4. Share a deck with classmates via link

**Pages:**
- Home: My decks, study streak counter, "Continue Studying" button
- Create: Add new cards with a front (question) and back (answer)
- Study: Shows one card at a time, tap to flip, buttons for Easy/Hard/Again
- Stats: Simple charts showing how many cards reviewed per day

**Style**: Clean, dark mode, similar to Anki but more modern

**Data to save**: Flashcard decks, individual cards, study progress per card

**Demo**: Open app -> see my decks -> tap "Biology 101" -> study 3 cards by flipping and rating -> go back and see my streak increase
