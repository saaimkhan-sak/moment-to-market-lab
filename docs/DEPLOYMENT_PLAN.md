# Deployment plan

One repository, one shared codebase, and one eventual Vercel project. Club routes use `/clubs/{club_slug}`. The browser release generates a compact index plus one evidence bundle per club, so an initial route does not download the full league archive. No deployment is created by this repository; a later scripted matrix may map configured clubs to domains without duplicating the codebase.
