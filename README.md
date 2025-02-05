# pyviddbcreator
Python scripts and modules to automatically segment and sort video clips for use in vision psychology/neuroscience experiments.

The first few steps are accomplished via the pipeline scripts,
followed by a "judgement" step (manual judgement of clips by a human
-- using a website which presents the clips to users and allows them
to judge them "good" or "not good"). This step can also be automated.

The code for the django-based clip-selection website is in clipselectorapp/