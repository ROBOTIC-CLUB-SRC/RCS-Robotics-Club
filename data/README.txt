The club application no longer uses this local SQLite directory. Configure
`DATABASE_URL` with the Supabase PostgreSQL connection string; the required
tables are created in Supabase on startup. Do not add local database files to
the application.
