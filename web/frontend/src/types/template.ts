/** Template-related type definitions. */

export interface TemplateInfo {
  id: string
  name: string
  name_en: string
  name_zh: string
  description_en: string
  description_zh: string
  category: string
  tags: string[]
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  available: boolean
  prompt_en?: string
  prompt_zh?: string
}

export interface TemplateDetail extends TemplateInfo {
  yaml_content: string
  prompt_en: string
  prompt_zh: string
}
