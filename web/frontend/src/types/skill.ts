export interface SkillModule {
  id: string
  name: string
  description: string
  token_estimate: number
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
