import {
  checkProjectVersion,
  type ProjectVersionInfoResponse
} from '../api/projectInfo'

const CACHE_KEY = 'promptworks-project-version-check'
export const PROJECT_VERSION_CHECK_EVENT = 'promptworks-project-version-check'

interface VersionCheckCache {
  checkedDate: string
  version: ProjectVersionInfoResponse
}

function todayKey(): string {
  return new Date().toISOString().slice(0, 10)
}

function readCache(): VersionCheckCache | null {
  const raw = window.localStorage.getItem(CACHE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as VersionCheckCache
  } catch {
    window.localStorage.removeItem(CACHE_KEY)
    return null
  }
}

function isResolvedCheck(version: ProjectVersionInfoResponse): boolean {
  return version.check_status !== 'unknown'
}

export function readCachedProjectVersionCheck(): ProjectVersionInfoResponse | null {
  const cache = readCache()
  return cache?.version ?? null
}

export function writeProjectVersionCheckCache(
  version: ProjectVersionInfoResponse
): void {
  window.localStorage.setItem(
    CACHE_KEY,
    JSON.stringify({ checkedDate: todayKey(), version })
  )
  window.dispatchEvent(
    new CustomEvent<ProjectVersionInfoResponse>(PROJECT_VERSION_CHECK_EVENT, {
      detail: version
    })
  )
}

export async function checkProjectVersionOncePerDay(): Promise<ProjectVersionInfoResponse | null> {
  const cache = readCache()
  if (cache?.checkedDate === todayKey() && isResolvedCheck(cache.version)) {
    return cache.version
  }

  const version = await checkProjectVersion()
  writeProjectVersionCheckCache(version)
  return version
}
