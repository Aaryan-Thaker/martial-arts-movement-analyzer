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
  instructorNotes?: string;
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

export default function EditorPage() {
  const router = useRouter();

  const videoRef = useRef<HTMLVideoElement>(null);

  const [kata, setKata] = useState<Kata | null>(null);

  const [currentMovement, setCurrentMovement] =
    useState(0);

  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const [isPlaying, setIsPlaying] = useState(false);

  const [playbackMode, setPlaybackMode] = useState<
    "movement" | "continuous"
  >("movement");

  const [saved, setSaved] = useState(false);
  const [autoSaved, setAutoSaved] = useState(false);

  const [splitTime, setSplitTime] = useState<number | null>(
    null
  );

  const movement = kata?.movements[currentMovement];

  /*
   * ====================================================
   * LOAD KATA
   * ====================================================
   */

  useEffect(() => {
    async function loadKata() {
      try {
        const localData = localStorage.getItem(
          "martial-arts-ai-heian-shodan"
        );

        if (localData) {
          try {
            const parsed: Kata = JSON.parse(localData);

            if (
              parsed &&
              Array.isArray(parsed.movements) &&
              parsed.movements.length > 0
            ) {
              setKata(parsed);
              return;
            }
          } catch {
            console.warn(
              "Could not read autosaved kata."
            );
          }
        }

        const response = await fetch(
          "/heian_shodan.json"
        );

        if (!response.ok) {
          throw new Error("Could not load kata");
        }

        const data: Kata = await response.json();

        setKata(data);
      } catch (error) {
        console.error(
          "Failed to load kata:",
          error
        );
      }
    }

    loadKata();
  }, []);

  /*
   * ====================================================
   * AUTOSAVE
   * ====================================================
   */

  useEffect(() => {
    if (!kata) {
      return;
    }

    const timer = setTimeout(() => {
      try {
        localStorage.setItem(
          "martial-arts-ai-heian-shodan",
          JSON.stringify(kata)
        );

        setAutoSaved(true);

        const hideTimer = setTimeout(() => {
          setAutoSaved(false);
        }, 1500);

        return () => clearTimeout(hideTimer);
      } catch (error) {
        console.error(
          "Autosave failed:",
          error
        );
      }
    }, 500);

    return () => {
      clearTimeout(timer);
    };
  }, [kata]);

  /*
   * ====================================================
   * LIVE VIDEO CLOCK
   *
   * IMPORTANT:
   *
   * We deliberately do NOT use "timeupdate" here.
   *
   * timeupdate is too infrequent for an editor timeline.
   *
   * requestAnimationFrame reads video.currentTime
   * continuously while the video is playing.
   * ====================================================
   */

  useEffect(() => {
    const video = videoRef.current;

    if (!video) {
      return;
    }

    let frameId: number | null = null;

    const updateClock = () => {
      /*
       * Read the real position of the video.
       */
      setCurrentTime(video.currentTime);

      /*
       * Continue while the video is playing.
       */
      if (!video.paused && !video.ended) {
        frameId =
          requestAnimationFrame(updateClock);
      } else {
        frameId = null;
      }
    };

    const startClock = () => {
      setIsPlaying(true);

      /*
       * Prevent multiple animation loops.
       */
      if (frameId !== null) {
        cancelAnimationFrame(frameId);
      }

      frameId =
        requestAnimationFrame(updateClock);
    };

    const stopClock = () => {
      setIsPlaying(false);

      /*
       * Get the exact final position.
       */
      setCurrentTime(video.currentTime);

      if (frameId !== null) {
        cancelAnimationFrame(frameId);
        frameId = null;
      }
    };

    const handleSeeked = () => {
      /*
       * Immediately update after seeking.
       */
      setCurrentTime(video.currentTime);
    };

    const handleLoadedMetadata = () => {
      if (Number.isFinite(video.duration)) {
        setDuration(video.duration);
      }

      setCurrentTime(video.currentTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);

      setCurrentTime(video.duration);

      if (frameId !== null) {
        cancelAnimationFrame(frameId);
        frameId = null;
      }
    };

    video.addEventListener(
      "play",
      startClock
    );

    video.addEventListener(
      "playing",
      startClock
    );

    video.addEventListener(
      "pause",
      stopClock
    );

    video.addEventListener(
      "seeked",
      handleSeeked
    );

    video.addEventListener(
      "loadedmetadata",
      handleLoadedMetadata
    );

    video.addEventListener(
      "ended",
      handleEnded
    );

    /*
     * If already playing when mounted.
     */
    if (!video.paused && !video.ended) {
      startClock();
    }

    return () => {
      video.removeEventListener(
        "play",
        startClock
      );

      video.removeEventListener(
        "playing",
        startClock
      );

      video.removeEventListener(
        "pause",
        stopClock
      );

      video.removeEventListener(
        "seeked",
        handleSeeked
      );

      video.removeEventListener(
        "loadedmetadata",
        handleLoadedMetadata
      );

      video.removeEventListener(
        "ended",
        handleEnded
      );

      if (frameId !== null) {
        cancelAnimationFrame(frameId);
      }
    };
  }, []);

  /*
   * ====================================================
   * SEGMENTED PLAYBACK
   * ====================================================
   */

  useEffect(() => {
    const video = videoRef.current;

    if (!video || !movement) {
      return;
    }

    let checking = false;

    const checkMovementEnd = () => {
      if (
        playbackMode !== "movement" ||
        video.paused
      ) {
        return;
      }

      /*
       * Use the real video position.
       */
      if (video.currentTime >= movement.end) {
        checking = true;

        video.pause();

        video.currentTime = movement.end;

        setCurrentTime(movement.end);

        setIsPlaying(false);

        checking = false;
      }
    };

    /*
     * We intentionally use requestAnimationFrame for
     * movement stopping too, so the segment cannot
     * overshoot badly between timeupdate events.
     */

    const loop = () => {
      if (!checking) {
        checkMovementEnd();
      }

      if (
        !video.paused &&
        playbackMode === "movement"
      ) {
        requestAnimationFrame(loop);
      }
    };

    const startChecking = () => {
      requestAnimationFrame(loop);
    };

    video.addEventListener(
      "playing",
      startChecking
    );

    return () => {
      video.removeEventListener(
        "playing",
        startChecking
      );
    };
  }, [movement, playbackMode]);

  /*
   * ====================================================
   * UPDATE MOVEMENT
   * ====================================================
   */

  const updateMovement = (
    field: keyof Movement,
    value: string | number | boolean
  ) => {
    if (!kata) {
      return;
    }

    const movements = [...kata.movements];

    movements[currentMovement] = {
      ...movements[currentMovement],
      [field]: value,
    };

    setKata({
      ...kata,
      movements,
    });

    setSaved(false);
  };

  /*
   * ====================================================
   * SET VIDEO TIME
   * ====================================================
   */

  const setVideoTime = (time: number) => {
    const video = videoRef.current;

    if (!video) {
      return;
    }

    const maxTime = Number.isFinite(
      video.duration
    )
      ? video.duration
      : duration;

    const safeTime = Math.max(
      0,
      Math.min(time, maxTime || time)
    );

    video.currentTime = safeTime;

    /*
     * Update immediately.
     */
    setCurrentTime(safeTime);
  };

  /*
   * ====================================================
   * SELECT MOVEMENT
   * ====================================================
   */

  const selectMovement = (index: number) => {
    if (!kata) {
      return;
    }

    if (
      index < 0 ||
      index >= kata.movements.length
    ) {
      return;
    }

    const video = videoRef.current;

    if (video) {
      video.pause();
    }

    setIsPlaying(false);
    setPlaybackMode("movement");
    setCurrentMovement(index);

    const selectedMovement =
      kata.movements[index];

    /*
     * Move after React updates state.
     */
    requestAnimationFrame(() => {
      const currentVideo =
        videoRef.current;

      if (!currentVideo) {
        return;
      }

      currentVideo.currentTime =
        selectedMovement.start;

      setCurrentTime(
        selectedMovement.start
      );
    });
  };

  /*
   * ====================================================
   * PREVIOUS MOVEMENT
   * ====================================================
   */

  const previousMovement = () => {
    if (currentMovement <= 0) {
      return;
    }

    selectMovement(
      currentMovement - 1
    );
  };

  /*
   * ====================================================
   * NEXT MOVEMENT
   * ====================================================
   */

  const nextMovement = () => {
    if (!kata) {
      return;
    }

    if (
      currentMovement >=
      kata.movements.length - 1
    ) {
      return;
    }

    selectMovement(
      currentMovement + 1
    );
  };

  /*
   * ====================================================
   * PLAY CURRENT MOVEMENT
   * ====================================================
   */

  const playMovement = async () => {
    const video = videoRef.current;

    if (!video || !movement) {
      return;
    }

    setPlaybackMode("movement");

    /*
     * Start at movement beginning.
     */
    video.currentTime =
      movement.start;

    setCurrentTime(
      movement.start
    );

    try {
      await video.play();
    } catch (error) {
      console.error(
        "Unable to play movement:",
        error
      );
    }
  };

  /*
   * ====================================================
   * PLAY CONTINUOUS
   * ====================================================
   */

  const playContinuous = async () => {
    const video = videoRef.current;

    if (!video) {
      return;
    }

    setPlaybackMode("continuous");

    if (
      Number.isFinite(video.duration) &&
      video.currentTime >=
        video.duration - 0.05
    ) {
      video.currentTime = 0;

      setCurrentTime(0);
    }

    try {
      await video.play();
    } catch (error) {
      console.error(
        "Unable to play video:",
        error
      );
    }
  };

  /*
   * ====================================================
   * PAUSE
   * ====================================================
   */

  const pauseVideo = () => {
    const video = videoRef.current;

    if (!video) {
      return;
    }

    video.pause();

    setCurrentTime(
      video.currentTime
    );
  };

  /*
   * ====================================================
   * SET START
   * ====================================================
   */

  const setStartFromVideo = () => {
    if (!movement) {
      return;
    }

    updateMovement(
      "start",
      Number(
        currentTime.toFixed(2)
      )
    );
  };

  /*
   * ====================================================
   * SET END
   * ====================================================
   */

  const setEndFromVideo = () => {
    if (!movement) {
      return;
    }

    updateMovement(
      "end",
      Number(
        currentTime.toFixed(2)
      )
    );
  };

  /*
   * ====================================================
   * SPLIT MOVEMENT
   *
   * Splitting creates TWO independent movements.
   *
   * Original:
   *
   * Movement 4
   * 10.00 → 20.00
   * description = "..."
   *
   * Split at 15.00:
   *
   * Movement 4
   * 10.00 → 15.00
   * description = original
   *
   * Movement 5
   * 15.00 → 20.00
   * description = ""
   *
   * This solves the issue where a description appears
   * to belong to the wrong technique.
   * ====================================================
   */

  const splitMovement = () => {
    if (!kata || !movement) {
      return;
    }

    const splitAt =
      splitTime ?? currentTime;

    /*
     * Split must be inside the movement.
     */
    if (
      splitAt <= movement.start + 0.01 ||
      splitAt >= movement.end - 0.01
    ) {
      alert(
        "The split point must be inside the movement's start and end times."
      );

      return;
    }

    const firstMovement: Movement = {
      ...movement,
      end: Number(
        splitAt.toFixed(2)
      ),
    };

    const secondMovement: Movement = {
      ...movement,

      /*
       * Give the second segment its own ID.
       */
      id: movement.id + 1,

      start: Number(
        splitAt.toFixed(2)
      ),

      /*
       * IMPORTANT:
       *
       * The second segment gets its own description
       * instead of inheriting the first technique's
       * description.
       */
      description: "",

      purpose: "",
      keyPoints: [],
      commonMistakes: [],
      bunkai: "",
      instructorNotes: "",
    };

    /*
     * Everything after the inserted movement needs
     * its own sequential ID.
     */
    const newMovements = [
      ...kata.movements.slice(
        0,
        currentMovement
      ),

      firstMovement,

      secondMovement,

      ...kata.movements.slice(
        currentMovement + 1
      ),
    ].map(
      (item, index) => ({
        ...item,
        id: index + 1,
      })
    );

    setKata({
      ...kata,
      movements: newMovements,
      movementCount:
        newMovements.length,
    });

    /*
     * Select the newly created second segment.
     */
    setCurrentMovement(
      currentMovement + 1
    );

    setSplitTime(null);

    requestAnimationFrame(() => {
      const video =
        videoRef.current;

      if (!video) {
        return;
      }

      video.pause();

      video.currentTime =
        splitAt;

      setCurrentTime(splitAt);
      setIsPlaying(false);
      setPlaybackMode("movement");
    });
  };

  /*
   * ====================================================
   * MERGE WITH PREVIOUS
   * ====================================================
   */

  const mergeWithPrevious = () => {
    if (
      !kata ||
      currentMovement <= 0
    ) {
      return;
    }

    const previous =
      kata.movements[
        currentMovement - 1
      ];

    const current =
      kata.movements[
        currentMovement
      ];

    /*
     * Keep the previous movement's main
     * description/content unless it is empty.
     */
    const merged: Movement = {
      ...previous,

      end: current.end,

      description:
        previous.description ||
        current.description,

      purpose:
        previous.purpose ||
        current.purpose,

      keyPoints:
        previous.keyPoints.length > 0
          ? previous.keyPoints
          : current.keyPoints,

      commonMistakes:
        previous.commonMistakes.length > 0
          ? previous.commonMistakes
          : current.commonMistakes,

      bunkai:
        previous.bunkai ||
        current.bunkai,

      instructorNotes:
        previous.instructorNotes ||
        current.instructorNotes,

      /*
       * Preserve KIAI if either section has it.
       */
      kiai:
        previous.kiai ||
        current.kiai,
    };

    const newMovements = [
      ...kata.movements.slice(
        0,
        currentMovement - 1
      ),

      merged,

      ...kata.movements.slice(
        currentMovement + 1
      ),
    ].map(
      (item, index) => ({
        ...item,
        id: index + 1,
      })
    );

    setKata({
      ...kata,
      movements: newMovements,
      movementCount:
        newMovements.length,
    });

    setCurrentMovement(
      currentMovement - 1
    );

    requestAnimationFrame(() => {
      const video =
        videoRef.current;

      if (!video) {
        return;
      }

      video.pause();

      video.currentTime =
        merged.start;

      setCurrentTime(
        merged.start
      );

      setIsPlaying(false);
      setPlaybackMode("movement");
    });
  };

  /*
   * ====================================================
   * SAVE CHANGES
   * ====================================================
   */

  const saveChanges = () => {
    if (!kata) {
      return;
    }

    localStorage.setItem(
      "martial-arts-ai-heian-shodan",
      JSON.stringify(kata)
    );

    const json =
      JSON.stringify(
        kata,
        null,
        2
      );

    const blob = new Blob(
      [json],
      {
        type: "application/json",
      }
    );

    const url =
      URL.createObjectURL(blob);

    const link =
      document.createElement("a");

    link.href = url;
    link.download =
      "heian_shodan.json";

    document.body.appendChild(
      link
    );

    link.click();

    document.body.removeChild(
      link
    );

    URL.revokeObjectURL(url);

    setSaved(true);

    setTimeout(() => {
      setSaved(false);
    }, 2000);
  };

  /*
   * ====================================================
   * FORMAT TIME
   * ====================================================
   */

  const formatTime = (
    time: number
  ) => {
    if (
      !Number.isFinite(time)
    ) {
      return "00:00.00";
    }

    const minutes =
      Math.floor(time / 60);

    const seconds =
      time % 60;

    return `${String(
      minutes
    ).padStart(
      2,
      "0"
    )}:${seconds
      .toFixed(2)
      .padStart(
        5,
        "0"
      )}`;
  };

  /*
   * ====================================================
   * KEYBOARD CONTROLS
   * ====================================================
   */

  useEffect(() => {
    const handleKeyboard = (
      event: KeyboardEvent
    ) => {
      const target =
        event.target as HTMLElement;

      /*
       * Don't hijack keyboard input fields.
       */
      if (
        target.tagName ===
          "INPUT" ||
        target.tagName ===
          "TEXTAREA"
      ) {
        return;
      }

      if (
        event.key ===
        "ArrowLeft"
      ) {
        event.preventDefault();

        previousMovement();
      }

      if (
        event.key ===
        "ArrowRight"
      ) {
        event.preventDefault();

        nextMovement();
      }

      if (
        event.key ===
        " "
      ) {
        event.preventDefault();

        const video =
          videoRef.current;

        if (!video) {
          return;
        }

        if (video.paused) {
          if (
            playbackMode ===
            "movement"
          ) {
            playMovement();
          } else {
            playContinuous();
          }
        } else {
          pauseVideo();
        }
      }
    };

    window.addEventListener(
      "keydown",
      handleKeyboard
    );

    return () => {
      window.removeEventListener(
        "keydown",
        handleKeyboard
      );
    };
  });

  /*
   * ====================================================
   * LOADING
   * ====================================================
   */

  if (
    !kata ||
    !movement
  ) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-zinc-950 text-white">
        <p className="text-zinc-400">
          Loading editor...
        </p>
      </main>
    );
  }

  /*
   * ====================================================
   * MAIN UI
   * ====================================================
   */

  return (
    <main className="min-h-screen bg-zinc-950 text-white">

      {/* HEADER */}

      <nav className="sticky top-0 z-20 border-b border-white/10 bg-zinc-950/90 backdrop-blur-xl">

        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">

          <button
            onClick={() =>
              router.push("/")
            }
            className="font-semibold tracking-tight transition hover:text-zinc-300"
          >
            Martial Arts AI
          </button>

          <div className="flex gap-2">

            <button
              onClick={() =>
                router.push(
                  "/training"
                )
              }
              className="rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-400 transition hover:bg-white/10 hover:text-white"
            >
              Training
            </button>

            <button
              onClick={
                saveChanges
              }
              className="rounded-lg bg-white px-3 py-2 text-xs font-semibold text-black transition hover:bg-zinc-200"
            >
              {saved
                ? "Saved ✓"
                : "Save"}
            </button>

          </div>

        </div>

      </nav>


      {/* PAGE */}

      <div className="mx-auto max-w-5xl px-4 py-6">

        {/* TITLE */}

        <div className="mb-5 flex items-end justify-between">

          <div>

            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-600">
              Instructor Editor
            </p>

            <h1 className="mt-1 text-2xl font-bold">
              {kata.name}
            </h1>

          </div>

          {autoSaved && (
            <span className="text-xs text-zinc-600">
              Saved
            </span>
          )}

        </div>


        {/* MOVEMENT SELECTOR */}

        <div className="mb-4 flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.025] p-3">

          <button
            onClick={
              previousMovement
            }
            disabled={
              currentMovement ===
              0
            }
            className="rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-400 transition hover:bg-white/10 disabled:opacity-20"
          >
            ← Previous
          </button>

          <div className="text-center">

            <div className="font-mono text-sm text-zinc-500">
              Movement{" "}
              {movement.id}{" "}
              /{" "}
              {kata.movements.length}
            </div>

            <div className="mt-0.5 text-sm font-medium text-zinc-300">
              {movement.name ||
                "Unnamed movement"}
            </div>

          </div>

          <button
            onClick={
              nextMovement
            }
            disabled={
              currentMovement ===
              kata.movements.length -
                1
            }
            className="rounded-lg bg-white px-3 py-2 text-xs font-semibold text-black transition hover:bg-zinc-200 disabled:opacity-20"
          >
            Next →
          </button>

        </div>


        {/* VIDEO */}

        <div className="overflow-hidden rounded-xl border border-white/10 bg-black">

          <video
            ref={videoRef}
            src={`/${kata.video}`}
            className="mx-auto block max-h-[62vh] w-full object-contain"
            playsInline
            controls={false}
          />

        </div>


        {/* TIMELINE */}

        <div className="mt-3 rounded-xl border border-white/10 bg-white/[0.025] p-4">

          <div className="flex items-end justify-between">

            <div>

              <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-600">
                Video Time
              </p>

              <p className="mt-1 font-mono text-2xl font-bold tabular-nums">
                {formatTime(
                  currentTime
                )}
              </p>

            </div>

            <p className="font-mono text-xs text-zinc-600">
              /
              {" "}
              {formatTime(
                duration
              )}
            </p>

          </div>


          {/* LIVE SEEK BAR */}

          <input
            type="range"
            min={0}
            max={
              duration || 0
            }
            step={0.01}
            value={
              Math.min(
                currentTime,
                duration || currentTime
              )
            }
            onChange={(
              event
            ) =>
              setVideoTime(
                Number(
                  event.target
                    .value
                )
              )
            }
            className="mt-3 h-2 w-full cursor-pointer accent-white"
          />


          {/* MOVEMENT RANGE */}

          <div className="mt-3 flex items-center justify-between text-xs">

            <span className="text-zinc-600">
              Movement range
            </span>

            <span className="font-mono text-zinc-400">
              {formatTime(
                movement.start
              )}
              {" → "}
              {formatTime(
                movement.end
              )}
            </span>

          </div>


          {/* CONTROLS */}

          <div className="mt-4 grid grid-cols-3 gap-2">

            <button
              onClick={
                playMovement
              }
              className={`rounded-lg px-3 py-3 text-xs font-semibold transition ${
                playbackMode ===
                  "movement" &&
                isPlaying
                  ? "bg-white text-black"
                  : "border border-white/10 bg-white/[0.02] text-zinc-400 hover:bg-white/10"
              }`}
            >
              ▶ Movement
            </button>

            <button
              onClick={
                playContinuous
              }
              className={`rounded-lg px-3 py-3 text-xs font-semibold transition ${
                playbackMode ===
                  "continuous" &&
                isPlaying
                  ? "bg-white text-black"
                  : "border border-white/10 bg-white/[0.02] text-zinc-400 hover:bg-white/10"
              }`}
            >
              ▶ Play All
            </button>

            <button
              onClick={
                pauseVideo
              }
              className="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-3 text-xs font-semibold text-zinc-400 transition hover:bg-white/10 hover:text-white"
            >
              ❚❚ Pause
            </button>

          </div>

        </div>


        {/* SPLIT / MERGE */}

        <div className="mt-3 rounded-xl border border-white/10 bg-white/[0.025] p-4">

          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">

            <div>

              <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-600">
                Segment Editing
              </p>

              <p className="mt-1 text-xs text-zinc-500">
                Split the current movement at the
                current video position, or merge it
                with the previous movement.
              </p>

            </div>

            <div className="flex gap-2">

              <button
                onClick={() =>
                  setSplitTime(
                    Number(
                      currentTime.toFixed(
                        2
                      )
                    )
                  )
                }
                className="rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-400 transition hover:bg-white/10 hover:text-white"
              >
                Mark Split
              </button>

              <button
                onClick={
                  splitMovement
                }
                className="rounded-lg bg-white px-3 py-2 text-xs font-semibold text-black transition hover:bg-zinc-200"
              >
                Split Movement
              </button>

              <button
                onClick={
                  mergeWithPrevious
                }
                disabled={
                  currentMovement ===
                  0
                }
                className="rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-400 transition hover:bg-white/10 disabled:opacity-20"
              >
                Merge Previous
              </button>

            </div>

          </div>

          {splitTime !==
            null && (
            <div className="mt-3 flex items-center justify-between rounded-lg bg-black/30 px-3 py-2 text-xs">

              <span className="text-zinc-600">
                Split point
              </span>

              <div className="flex items-center gap-3">

                <span className="font-mono text-zinc-300">
                  {formatTime(
                    splitTime
                  )}
                </span>

                <button
                  onClick={() =>
                    setSplitTime(
                      null
                    )
                  }
                  className="text-zinc-600 hover:text-white"
                >
                  Cancel
                </button>

              </div>

            </div>
          )}

        </div>


        {/* MOVEMENT EDITOR */}

        <section className="mt-4 rounded-xl border border-white/10 bg-white/[0.025]">

          <div className="border-b border-white/10 px-4 py-4">

            <div className="flex items-center justify-between">

              <div>

                <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-600">
                  Movement Information
                </p>

                <h2 className="mt-1 text-lg font-semibold">
                  {movement.name ||
                    `Movement ${movement.id}`}
                </h2>

              </div>

              {movement.kiai && (
                <span className="rounded-full border border-white/10 px-2 py-1 text-[9px] font-bold text-zinc-500">
                  KIAI
                </span>
              )}

            </div>

          </div>


          <div className="space-y-7 p-4">

            {/* TIMING */}

            <div>

              <div className="flex items-center justify-between">

                <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-600">
                  Timing
                </p>

                <span className="font-mono text-[10px] text-zinc-600">
                  Current{" "}
                  {formatTime(
                    currentTime
                  )}
                </span>

              </div>

              <div className="mt-3 grid gap-3 sm:grid-cols-2">

                <div>

                  <label className="text-xs text-zinc-600">
                    Start
                  </label>

                  <input
                    type="number"
                    step="0.01"
                    value={
                      movement.start
                    }
                    onChange={(
                      event
                    ) =>
                      updateMovement(
                        "start",
                        Number(
                          event.target
                            .value
                        )
                      )
                    }
                    className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 font-mono text-sm outline-none focus:border-white/30"
                  />

                  <button
                    onClick={
                      setStartFromVideo
                    }
                    className="mt-1.5 text-[10px] text-zinc-600 hover:text-white"
                  >
                    Use current video time
                  </button>

                </div>

                <div>

                  <label className="text-xs text-zinc-600">
                    End
                  </label>

                  <input
                    type="number"
                    step="0.01"
                    value={
                      movement.end
                    }
                    onChange={(
                      event
                    ) =>
                      updateMovement(
                        "end",
                        Number(
                          event.target
                            .value
                        )
                      )
                    }
                    className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 font-mono text-sm outline-none focus:border-white/30"
                  />

                  <button
                    onClick={
                      setEndFromVideo
                    }
                    className="mt-1.5 text-[10px] text-zinc-600 hover:text-white"
                  >
                    Use current video time
                  </button>

                </div>

              </div>

            </div>


            {/* TECHNIQUE */}

            <div>

              <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-600">
                Technique
              </p>

              <div className="mt-3 grid gap-3 sm:grid-cols-2">

                <div>

                  <label className="text-xs text-zinc-600">
                    Technique Name
                  </label>

                  <input
                    value={
                      movement.name
                    }
                    onChange={(
                      event
                    ) =>
                      updateMovement(
                        "name",
                        event.target
                          .value
                      )
                    }
                    className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 text-sm outline-none focus:border-white/30"
                  />

                </div>

                <div>

                  <label className="text-xs text-zinc-600">
                    Japanese Name
                  </label>

                  <input
                    value={
                      movement.japaneseName
                    }
                    onChange={(
                      event
                    ) =>
                      updateMovement(
                        "japaneseName",
                        event.target
                          .value
                      )
                    }
                    className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 text-sm outline-none focus:border-white/30"
                  />

                </div>

                <div>

                  <label className="text-xs text-zinc-600">
                    Stance
                  </label>

                  <input
                    value={
                      movement.stance
                    }
                    onChange={(
                      event
                    ) =>
                      updateMovement(
                        "stance",
                        event.target
                          .value
                      )
                    }
                    className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 text-sm outline-none focus:border-white/30"
                  />

                </div>

                <label className="flex items-center gap-2 rounded-lg border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-zinc-400">

                  <input
                    type="checkbox"
                    checked={
                      movement.kiai
                    }
                    onChange={(
                      event
                    ) =>
                      updateMovement(
                        "kiai",
                        event.target
                          .checked
                      )
                    }
                    className="accent-white"
                  />

                  Kiai

                </label>

              </div>

            </div>


            {/* DESCRIPTION */}

            <div>

              <div className="flex items-center justify-between">

                <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-600">
                  Description
                </p>

                <button
                  onClick={() =>
                    updateMovement(
                      "description",
                      ""
                    )
                  }
                  className="text-[10px] text-zinc-600 hover:text-white"
                >
                  Clear
                </button>

              </div>

              <textarea
                value={
                  movement.description
                }
                onChange={(
                  event
                ) =>
                  updateMovement(
                    "description",
                    event.target.value
                  )
                }
                rows={5}
                placeholder="Write a description for this movement..."
                className="mt-2 w-full resize-y rounded-lg border border-white/10 bg-black/30 p-3 text-sm leading-6 outline-none focus:border-white/30"
              />

            </div>


            {/* BUNKAI */}

            <div>

              <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-600">
                Bunkai
              </p>

              <textarea
                value={
                  movement.bunkai
                }
                onChange={(
                  event
                ) =>
                  updateMovement(
                    "bunkai",
                    event.target.value
                  )
                }
                rows={4}
                placeholder="Describe the bunkai..."
                className="mt-2 w-full resize-y rounded-lg border border-white/10 bg-black/30 p-3 text-sm leading-6 outline-none focus:border-white/30"
              />

            </div>


            {/* INSTRUCTOR NOTES */}

            <div>

              <p className="text-[9px] font-semibold uppercase tracking-[0.18em] text-zinc-600">
                Instructor Notes
              </p>

              <textarea
                value={
                  movement.instructorNotes ??
                  ""
                }
                onChange={(
                  event
                ) =>
                  updateMovement(
                    "instructorNotes",
                    event.target.value
                  )
                }
                rows={4}
                placeholder="Optional instructor notes..."
                className="mt-2 w-full resize-y rounded-lg border border-white/10 bg-black/30 p-3 text-sm leading-6 outline-none focus:border-white/30"
              />

            </div>


            {/* NAVIGATION */}

            <div className="flex items-center justify-between border-t border-white/10 pt-5">

              <button
                onClick={
                  previousMovement
                }
                disabled={
                  currentMovement ===
                  0
                }
                className="rounded-lg border border-white/10 px-4 py-2.5 text-xs text-zinc-400 transition hover:bg-white/10 disabled:opacity-20"
              >
                ← Previous
              </button>

              <span className="font-mono text-[10px] text-zinc-700">
                {movement.id}
                {" / "}
                {
                  kata.movements
                    .length
                }
              </span>

              <button
                onClick={
                  nextMovement
                }
                disabled={
                  currentMovement ===
                  kata.movements.length -
                    1
                }
                className="rounded-lg bg-white px-4 py-2.5 text-xs font-semibold text-black transition hover:bg-zinc-200 disabled:opacity-20"
              >
                Next →
              </button>

            </div>

          </div>

        </section>


        {/* FOOTER HELP */}

        <div className="py-5 text-center text-[10px] text-zinc-700">

          Space
          {" "}
          play/pause
          {" · "}
          ← →
          {" "}
          navigate movements

        </div>

      </div>

    </main>
  );
}