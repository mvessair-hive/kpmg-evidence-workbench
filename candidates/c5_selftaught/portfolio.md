# Intake agent — notes (included work sample)

*(SYNTHETIC ARTIFACT — fictional)*

The agent classifies a form into one of five types and extracts key fields. The
classifier is the LLM; the routing and the write to the ticketing system are
deterministic. Anything below 0.75 confidence, or any form mentioning a refund,
goes to a human first. I keep a 60-item labeled set and rerun it before each
change; I added 12 multilingual samples after I found the classifier weak on
French intake.
