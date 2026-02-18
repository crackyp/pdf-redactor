-- Run this in your Supabase SQL Editor to set up the database

-- Users table to track subscription status
create table if not exists users (
  id uuid references auth.users primary key,
  email text,
  tier text default 'free' check (tier in ('free', 'premium')),
  stripe_customer_id text,
  created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Enable Row Level Security
alter table users enable row level security;

-- Policy: Users can read their own data
create policy "Users can read own data" on users
  for select using (auth.uid() = id);

-- Policy: Users can insert their own data
create policy "Users can insert own data" on users
  for insert with check (auth.uid() = id);

-- Policy: Service role can update (for Stripe webhooks)
create policy "Service role can update" on users
  for update using (true);
