"use client";

import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  return (
    <main className="min-h-screen bg-zinc-950 text-white">

      {/* Navigation */}
      <nav className="border-b border-white/10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">

          {/* Logo */}
          <button
            onClick={() => router.push("/")}
            className="text-xl font-bold tracking-tight"
          >
            Martial Arts AI
          </button>

          {/* Navigation Links */}
          <div className="flex items-center gap-3 text-sm">

            <button
              onClick={() => router.push("/training")}
              className="rounded-lg px-3 py-2 text-zinc-400 transition hover:bg-white/10 hover:text-white"
            >
              Training
            </button>

            <button
              onClick={() => router.push("/editor")}
              className="rounded-lg px-3 py-2 text-zinc-400 transition hover:bg-white/10 hover:text-white"
            >
              Instructor
            </button>

          </div>
        </div>
      </nav>


      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 pb-16 pt-20">

        <div className="max-w-3xl">

          <p className="mb-4 text-sm font-medium uppercase tracking-[0.25em] text-zinc-400">
            Martial Arts Training
          </p>

          <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
            Learn your kata.
            <br />

            <span className="text-zinc-400">
              One movement at a time.
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-8 text-zinc-400">
            Study your kata one technique at a time, understand the
            movement, explore its bunkai, and eventually receive
            AI-powered feedback on your own technique.
          </p>

        </div>

      </section>


      {/* Katas */}
      <section className="mx-auto max-w-6xl px-6 pb-20">

        <div className="mb-6">

          <h2 className="text-2xl font-semibold">
            Katas
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Choose a kata to begin training.
          </p>

        </div>


        {/* Kata Grid */}
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">

          {/* Heian Shodan */}
          <div
            className="group rounded-2xl border border-white/10 bg-white/[0.03] p-6 transition hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.06]"
          >

            {/* Card Header */}
            <div className="mb-8 flex items-start justify-between">

              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 text-xl">
                🥋
              </div>

              <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-zinc-400">
                Karate
              </span>

            </div>


            {/* Kata Information */}
            <h3 className="text-xl font-semibold">
              Heian Shodan
            </h3>

            <p className="mt-2 text-sm text-zinc-400">
              Shotokan Karate
            </p>


            {/* Card Footer */}
            <div className="mt-6 flex items-center justify-between">

              <span className="text-sm text-zinc-500">
                21 movements
              </span>


              <div className="flex items-center gap-4">

                {/* Instructor */}
                <button
                  onClick={() => router.push("/editor")}
                  className="text-sm text-zinc-500 transition hover:text-white"
                >
                  Edit
                </button>


                {/* Training */}
                <button
                  onClick={() => router.push("/training")}
                  className="text-sm text-white transition hover:translate-x-1"
                >
                  Start →
                </button>

              </div>

            </div>

          </div>

        </div>

      </section>

    </main>
  );
}