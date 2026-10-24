import { useState } from "react";
import {
  IconArrowLeft,
  IconArrowRight,
  IconEye,
  IconEyeOff,
  IconInfoCircle,
  IconLockSquare,
  IconMail,
  IconScan,
} from "@tabler/icons-react";

const STORY_IMAGE =
  "https://api.builder.io/api/v1/image/assets/TEMP/06da568bc6a8e2175652150bcc62bbad24570645?width=1064";

function WelcomeStory() {
  return (
    <aside className="flex w-full shrink-0 flex-col gap-11 bg-[#123E30] px-6 py-12 sm:p-16 lg:min-h-screen lg:w-165">
      <div className="flex items-center gap-2.25">
        <div className="flex h-8.5 w-8 items-center justify-center rounded-2.25 bg-[#F7F7F0]">
          <IconScan size={22} stroke={1.7} color="#123E30" />
        </div>
        <span className="font-dm text-6.25 text-[#F7F7F0]">CheckAm</span>
      </div>
      <div className="flex flex-col gap-5">
        <span className="font-mono-plex text-xs font-medium uppercase text-[#BCD0C1]">
          Your everyday second look
        </span>
        <h2 className="font-dm text-10 font-normal leading-[1.08] sm:text-14.5 text-[#F7F7F0]">
          A little more clarity.
          <br />
          Every time you check.
        </h2>
        <p className="font-dm text-lg leading-normal text-[#BCD0C1]">
          Keep the evidence close. Save your checks, revisit a batch and follow
          the reports you’ve made.
        </p>
      </div>
      <img
        src={STORY_IMAGE}
        alt=""
        className="h-82.5 w-full rounded-2xl object-cover"
      />
      <div className="flex items-start gap-3">
        <IconInfoCircle
          size={20}
          stroke={1.7}
          color="#BCD0C1"
          className="shrink-0"
        />
        <p className="font-dm text-3.25 leading-normal text-[#BCD0C1]">
          Evidence to support your decisions. Not a regulator endorsement,
          laboratory test or safety guarantee.
        </p>
      </div>
    </aside>
  );
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const inputWrap =
    "flex min-h-12.5 items-center gap-3 rounded-lg border border-[#DCE2D8] bg-white p-3.5 focus-within:border-[#18543F] focus-within:ring-2 focus-within:ring-[#18543F]/20";
  const inputCls =
    "min-w-0 flex-1 bg-transparent font-dm text-sm text-[#203C32] outline-none placeholder:text-[#64746B]";

  return (
    <div className="flex min-h-screen flex-col bg-[#F7F7F0] lg:flex-row">
      <WelcomeStory />
      <main className="flex flex-1 flex-col gap-14 bg-white px-6 pb-10 pt-12 sm:px-12 md:px-25 lg:min-h-screen lg:px-12 xl:px-25">
        <a
          href="/"
          className="flex items-center justify-end gap-2 font-dm text-sm text-[#18543F] hover:underline"
        >
          <IconArrowLeft size={16} stroke={1.7} />
          Back to TrueCheck
        </a>

        <form
          className="flex w-full flex-col gap-6 pt-7.5"
          onSubmit={(e) => e.preventDefault()}
        >
          <div className="flex flex-col gap-3">
            <span className="font-mono-plex text-xs font-medium uppercase text-[#18543F]">
              Welcome back
            </span>
            <h1 className="font-dm text-8.5 font-semibold leading-normal text-[#123E30] sm:text-10.5">
              Your checks, in one place.
            </h1>
            <p className="font-dm text-4.25 leading-normal text-[#64746B]">
              Sign in to pick up where you left off.
            </p>
          </div>

          <label className="flex flex-col gap-2">
            <span className="font-dm text-sm font-semibold text-[#203C32]">
              Email address
            </span>
            <div className={inputWrap}>
              <input
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputCls}
              />
              <IconMail size={18} stroke={1.7} color="#18543F" />
            </div>
          </label>

          <div className="flex flex-col gap-2">
            <label className="flex flex-col gap-2">
              <span className="font-dm text-sm font-semibold text-[#203C32]">
                Password
              </span>
              <div className={inputWrap}>
                <input
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputCls}
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((v) => !v)}
                  className="text-[#18543F]"
                >
                  {showPassword ? (
                    <IconEyeOff size={18} stroke={1.7} />
                  ) : (
                    <IconEye size={18} stroke={1.7} />
                  )}
                </button>
              </div>
            </label>
            <div className="flex justify-end">
              <a
                href="#"
                className="font-dm text-sm font-semibold text-[#18543F] hover:underline"
              >
                Forgot password?
              </a>
            </div>
          </div>

          <button
            type="submit"
            className="flex h-13 items-center justify-center gap-3 rounded-lg border border-[#18543F] bg-[#18543F] px-5 font-dm text-3.75 text-white transition-colors hover:bg-[#123E30]"
          >
            <IconArrowRight size={19} stroke={1.7} />
            Sign in
          </button>

          <div className="flex items-start justify-center gap-1.5 font-dm text-sm">
            <span className="text-[#64746B]">New to TrueCheck?</span>
            <a href="#" className="text-[#18543F] hover:underline">
              Create an account
            </a>
          </div>

          <div className="flex items-center gap-4">
            <div className="h-px flex-1 bg-[#DCE2D8]" />
            <span className="font-dm text-xs text-[#64746B]">or</span>
            <div className="h-px flex-1 bg-[#DCE2D8]" />
          </div>

          <button
            type="button"
            className="flex h-13 items-center justify-center gap-3 rounded-lg border border-[#DCE2D8] bg-white px-5 font-dm text-3.75 text-[#18543F] transition-colors hover:bg-[#F7F7F0]"
          >
            <IconScan size={19} stroke={1.7} />
            Continue as guest
          </button>

          <p className="font-dm text-3.25 leading-normal text-[#64746B]">
            You don’t need an account to check a product. Sign in only when you
            want to keep a personal history.
          </p>
        </form>

        <div className="flex w-full flex-col gap-3">
          <div className="flex items-center gap-2">
            <IconLockSquare size={15} stroke={1.7} color="#18543F" />
            <span className="font-dm text-3.25 font-semibold text-[#18543F]">
              Your checks are yours.
            </span>
          </div>
          <p className="font-dm text-xs leading-normal text-[#64746B]">
            We don’t publish your identity or private seller details. By
            continuing, you agree to our Terms and Privacy notice.
          </p>
        </div>
      </main>
    </div>
  );
}