"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type Movement = {
  id: number;
  name: string;
  japaneseName: string;
  type: string;
  stance: string;
  start: number;
  end: number;
  kiai: boolean;
  description: string;
  purpose: string;
  keyPoints: string[];
  commonMistakes: string[];
  bunkai: string;
};

type Kata = {
  id: string;
  name: string;
  style: string;
  description: string;
  video: string;
  movementCount: number;
  movements: Movement[];
};

export default function TrainingPage() {
  const router = useRouter();

  const videoRef = useRef<HTMLVideoElement>(null);

  const [kata, setKata] = useState<Kata | null>(null);
  const [currentMovement, setCurrentMovement] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(true);

  const movement = kata?.movements[currentMovement];

  // --------------------------------------------------
  // Load kata data
  // --------------------------------------------------

  useEffect(() => {
    async function loadKata() {
      try {
        const response = await fetch("/heian_shodan.json");

        if (!response.ok) {
          throw new Error("Could not load kata data");
        }

        const data: Kata = await response.json();

        setKata(data);
      } catch (error) {
        console.error("Failed to load kata:", error);
      } finally {
        setLoading(false);
      }
    }

    loadKata();
  }, []);

  // --------------------------------------------------
  // Keep video at current movement
  // --------------------------------------------------

  useEffect(() => {
    if (!videoRef.current || !movement) {
      return;
    }

    videoRef.current.currentTime = movement.start;
    videoRef.current.pause();

    setIsPlaying(false);
  }, [currentMovement, movement]);

  // --------------------------------------------------
  // Check movement end
  // --------------------------------------------------

  useEffect(() => {
    const video = videoRef.current;

    if (!video) {
      return;
    }

    const handleTimeUpdate = () => {
      if (!movement) {
        return;
      }

      if (video.currentTime >= movement.end) {
        video.pause();

        video.currentTime = movement.end;

        setIsPlaying(false);
      }
    };

    video.addEventListener("timeupdate", handleTimeUpdate);

    return () => {
      video.removeEventListener(
        "timeupdate",
        handleTimeUpdate
      );
    };
  }, [movement]);

  // --------------------------------------------------
  // Play / pause
  // --------------------------------------------------

  const togglePlay = async () => {
    const video = videoRef.current;

    if (!video || !movement) {
      return;
    }

    if (video.paused) {
      if (
        video.currentTime < movement.start ||
        video.currentTime >= movement.end
      ) {
        video.currentTime = movement.start;
      }

      await video.play();

      setIsPlaying(true);
    } else {
      video.pause();

      setIsPlaying(false);
    }
  };

  // --------------------------------------------------
  // Previous movement
  // --------------------------------------------------

  const previousMovement = () => {
    if (currentMovement > 0) {
      setCurrentMovement(
        currentMovement - 1
      );
    }
  };

  // --------------------------------------------------
  // Next movement
  // --------------------------------------------------

  const nextMovement = () => {
    if (
      kata &&
      currentMovement < kata.movements.length - 1
    ) {
      setCurrentMovement(
        currentMovement + 1
      );
    }
  };

  // --------------------------------------------------
  // Jump to movement
  // --------------------------------------------------

  const selectMovement = (index: number) => {
    setCurrentMovement(index);
  };

  // --------------------------------------------------
  // Loading
  // --------------------------------------------------

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-950 text-white">
        <p className="text-zinc-400">
          Loading kata...
        </p>
      </main>
    );
  }

  // --------------------------------------------------
  // Error
  // --------------------------------------------------

  if (!kata || !movement) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-950 text-white">
        <div className="text-center">
          <h1 className="text-2xl font-semibold">
            Unable to load kata
          </h1>

          <p className="mt-2 text-zinc-400">
            Check that heian_shodan.json is inside
            the public folder.
          </p>

          <button
            onClick={() => router.push("/")}
            className="mt-6 rounded-lg bg-white px-5 py-2 text-sm font-medium text-black"
          >
            Back Home
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-zinc-950 text-white">

      {/* ------------------------------------------ */}
      {/* Navigation */}
      {/* ------------------------------------------ */}

      <nav className="border-b border-white/10">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">

          <button
            onClick={() => router.push("/")}
            className="text-xl font-bold tracking-tight"
          >
            Martial Arts AI
          </button>

          <button
            onClick={() => router.push("/")}
            className="text-sm text-zinc-400 transition hover:text-white"
          >
            ← Back to Katas
          </button>

        </div>
      </nav>


      {/* ------------------------------------------ */}
      {/* Main */}
      {/* ------------------------------------------ */}

      <div className="mx-auto max-w-7xl px-6 py-8">

        {/* Header */}

        <div className="mb-8">

          <p className="text-sm text-zinc-500">
            {kata.style}
          </p>

          <h1 className="mt-1 text-3xl font-bold">
            {kata.name}
          </h1>

        </div>


        {/* ---------------------------------------- */}
        {/* Video */}
        {/* ---------------------------------------- */}

        <div className="overflow-hidden rounded-2xl border border-white/10 bg-black">

          <video
            ref={videoRef}
            src={`/${kata.video}`}
            className="aspect-video w-full object-contain"
            playsInline
            controls={false}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />

        </div>


        {/* ---------------------------------------- */}
        {/* Controls */}
        {/* ---------------------------------------- */}

        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4">

          <div className="flex items-center justify-center gap-3">

            <button
              onClick={previousMovement}
              disabled={currentMovement === 0}
              className="rounded-xl border border-white/10 px-5 py-3 text-sm transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-30"
            >
              ← Previous
            </button>


            <button
              onClick={togglePlay}
              className="min-w-28 rounded-xl bg-white px-6 py-3 text-sm font-semibold text-black transition hover:bg-zinc-200"
            >
              {isPlaying ? "❚❚ Pause" : "▶ Play"}
            </button>


            <button
              onClick={nextMovement}
              disabled={
                currentMovement ===
                kata.movements.length - 1
              }
              className="rounded-xl border border-white/10 px-5 py-3 text-sm transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-30"
            >
              Next →
            </button>

          </div>

        </div>


        {/* ---------------------------------------- */}
        {/* Current movement */}
        {/* ---------------------------------------- */}

        <div className="mt-6">

          <div className="flex items-center justify-between">

            <div>

              <p className="text-sm text-zinc-500">
                Movement
              </p>

              <h2 className="text-2xl font-semibold">
                {currentMovement + 1}
                {" "}
                <span className="text-zinc-500">
                  / {kata.movements.length}
                </span>
              </h2>

            </div>


            {movement.kiai && (
              <div className="rounded-full border border-white/20 bg-white/10 px-4 py-2 text-sm font-semibold">
                KIAI
              </div>
            )}

          </div>


          {/* Progress */}

          <div className="mt-4 h-1 overflow-hidden rounded-full bg-white/10">

            <div
              className="h-full bg-white transition-all"
              style={{
                width: `${
                  ((currentMovement + 1) /
                    kata.movements.length) *
                  100
                }%`
              }}
            />

          </div>

        </div>


        {/* ---------------------------------------- */}
        {/* Movement selector */}
        {/* ---------------------------------------- */}

        <div className="mt-6 overflow-x-auto">

          <div className="flex gap-2 pb-2">

            {kata.movements.map(
              (item, index) => (

                <button
                  key={item.id}
                  onClick={() =>
                    selectMovement(index)
                  }
                  className={`min-w-12 rounded-lg px-3 py-2 text-sm transition ${
                    index === currentMovement
                      ? "bg-white text-black"
                      : "border border-white/10 bg-white/[0.03] text-zinc-400 hover:bg-white/10"
                  }`}
                >
                  {item.id}
                </button>

              )
            )}

          </div>

        </div>


        {/* ---------------------------------------- */}
        {/* Technique information */}
        {/* ---------------------------------------- */}

        <div className="mt-8 grid gap-6 lg:grid-cols-2">


          {/* Technique */}

          <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">

            <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Technique
            </p>

            <h2 className="mt-2 text-2xl font-semibold">
              {movement.name}
            </h2>

            <p className="mt-1 text-sm text-zinc-500">
              {movement.japaneseName}
            </p>


            <div className="mt-6 grid grid-cols-2 gap-4">

              <div>
                <p className="text-xs text-zinc-500">
                  Type
                </p>

                <p className="mt-1 text-sm">
                  {movement.type}
                </p>
              </div>


              <div>
                <p className="text-xs text-zinc-500">
                  Stance
                </p>

                <p className="mt-1 text-sm">
                  {movement.stance}
                </p>
              </div>

            </div>


            <div className="mt-6">

              <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">
                Description
              </p>

              <p className="mt-2 leading-7 text-zinc-300">
                {movement.description}
              </p>

            </div>

          </section>


          {/* Bunkai */}

          <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">

            <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Bunkai
            </p>

            {movement.bunkai ? (

              <p className="mt-4 leading-7 text-zinc-300">
                {movement.bunkai}
              </p>

            ) : (

              <div className="mt-4 rounded-xl border border-dashed border-white/10 p-5">

                <p className="text-sm text-zinc-500">
                  Bunkai has not been added yet.
                </p>

                <p className="mt-2 text-xs text-zinc-600">
                  This can be added later through
                  Instructor Mode.
                </p>

              </div>

            )}

          </section>

        </div>


        {/* ---------------------------------------- */}
        {/* Key points */}
        {/* ---------------------------------------- */}

        {movement.keyPoints.length > 0 && (

          <section className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-6">

            <p className="text-xs font-medium uppercase tracking-widest text-zinc-500">
              Key Points
            </p>

            <ul className="mt-4 space-y-2">

              {movement.keyPoints.map(
                (point, index) => (

                  <li
                    key={index}
                    className="text-sm text-zinc-300"
                  >
                    • {point}
                  </li>

                )
              )}

            </ul>

          </section>

        )}

      </div>

    </main>
  );
}