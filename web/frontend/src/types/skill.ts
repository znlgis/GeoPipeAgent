export interface SkillModule {
  id: string
  name: string
  description: string
  token_estimate: number
  source?: 'builtin' | 'external'
}

export interface SkillContentResponse {
  module: string
  content: string
  char_count: number
}

export interface SkillModulesResponse {
  modules: SkillModule[]
}

export interface SkillGenerateResponse {
  files: string[]
  output_dir: string
}

/** Skill settings used in chat requests */
export interface SkillSettings {
  enabled: boolean
  modules: string[]
}

/** Request body for importing a skill module from text content */
export interface SkillImportRequest {
  name: string
  description?: string
  content: string
}

/** Request body for importing a skill module from a URL */
export interface SkillImportUrlRequest {
  name: string
  description?: string
  url: string
}

/** Response from a skill import operation */
export interface SkillImportResponse {
  id: string
  name: string
  token_estimate: number
  char_count: number
}

/** Request body for updating an external skill module */
export interface SkillUpdateRequest {
  name?: string
  description?: string
  content?: string
}
