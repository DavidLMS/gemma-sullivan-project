import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, Clock, CheckCircle2, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { API_BASE } from '../config/api'

interface ContentItem {
  id: string
  name: string
  displayName: string
  status: 'building' | 'available'
  totalSections?: number
  viewedSections?: number
  lastViewed?: string
}

interface LearnSection {
  section_number: number
  content: string
}

interface LearnContent {
  type: string
  total_sections: number
  sections: LearnSection[]
}

// Parser to convert HTML tags to Markdown format
const parseHtmlToMarkdown = (content: string): string => {
  return content
    // Convert code blocks containing tables to proper GFM tables (FIRST PRIORITY)
    .replace(/```\n(.*?\|.*?\n(?:.*?\n)*?)```/gs, (match, tableContent) => {
      // Check if the content looks like a table (has | and --- separator)
      if (tableContent.includes('|') && tableContent.includes('---')) {
        // Remove the code block and convert to proper table format
        return tableContent
          .split('\n')
          .map(line => {
            const trimmed = line.trim()
            if (!trimmed) return ''
            
            if (trimmed.includes('|')) {
              // Ensure proper GFM table format
              if (!trimmed.startsWith('|')) {
                return `| ${trimmed} |`
              }
              if (!trimmed.endsWith('|')) {
                return `${trimmed} |`
              }
              return trimmed
            }
            return line
          })
          .join('\n')
          .trim() + '\n\n'
      }
      // If not a table, keep as code block
      return match
    })
    
    // Convert title tags to h1 markdown
    .replace(/<title>(.*?)<\/title>/gs, '# $1\n\n')
    // Convert p tags to paragraphs with double line breaks (use 's' flag for multiline)
    .replace(/<p>(.*?)<\/p>/gs, '$1\n\n')
    // Convert b tags to bold markdown
    .replace(/<b>(.*?)<\/b>/gs, '**$1**')
    // Convert text tags to plain text
    .replace(/<text>(.*?)<\/text>/gs, '$1')
    // Convert strong tags to bold markdown (in case they appear)
    .replace(/<strong>(.*?)<\/strong>/gs, '**$1**')
    // Convert em tags to italic markdown (in case they appear)
    .replace(/<em>(.*?)<\/em>/gs, '*$1*')
    // Convert i tags to italic markdown
    .replace(/<i>(.*?)<\/i>/gs, '*$1*')
    // Convert ordered lists (ol) to numbered markdown lists
    .replace(/<ol>(.*?)<\/ol>/gs, (match, listContent) => {
      let counter = 1
      const items = listContent.replace(/<li>(.*?)<\/li>/g, () => {
        const item = listContent.match(/<li>(.*?)<\/li>/g)?.[counter - 1]
        if (item) {
          const cleanItem = item.replace(/<li>(.*?)<\/li>/s, '$1').trim()
          return `${counter++}. ${cleanItem}\n`
        }
        return ''
      })
      // Process all li items properly
      const processedItems = listContent
        .match(/<li>(.*?)<\/li>/gs)
        ?.map((item, index) => {
          const cleanItem = item.replace(/<li>(.*?)<\/li>/s, '$1').trim()
          return `${index + 1}. ${cleanItem}`
        })
        .join('\n') || ''
      
      return processedItems + '\n\n'
    })
    // Convert unordered lists (ul) to bulleted markdown lists
    .replace(/<ul>(.*?)<\/ul>/gs, (match, listContent) => {
      const processedItems = listContent
        .match(/<li>(.*?)<\/li>/gs)
        ?.map(item => {
          const cleanItem = item.replace(/<li>(.*?)<\/li>/s, '$1').trim()
          return `- ${cleanItem}`
        })
        .join('\n') || ''
      
      return processedItems + '\n\n'
    })
    // Convert standalone li tags (outside of ol/ul) to bulleted items
    .replace(/<li>(.*?)<\/li>/gs, '- $1\n')
    
    // Convert table format to proper GFM format
    .replace(/(^.*?\|.*?\n^---.*?\n(?:^.*?\|.*?\n)*)/gm, (tableBlock) => {
      return tableBlock
        .split('\n')
        .map(line => {
          const trimmed = line.trim()
          if (!trimmed) return line
          
          if (trimmed.includes('|')) {
            // Add | at start and end if not present
            if (!trimmed.startsWith('|')) {
              return `| ${trimmed} |`
            }
            if (!trimmed.endsWith('|')) {
              return `${trimmed} |`
            }
            return trimmed
          }
          
          // Handle separator lines (--- | --- | ---)
          if (trimmed.includes('---')) {
            if (!trimmed.startsWith('|')) {
              // Convert "--- | --- | ---" to "|---|---|---|"
              const separated = trimmed.split('|').map(part => part.trim().replace(/\s+/g, '-'))
              return `|${separated.join('|')}|`
            }
            return trimmed
          }
          
          return line
        })
        .join('\n') + '\n\n'
    })
    
    // Clean up: Remove any remaining HTML tags that might have been missed
    .replace(/<[^>]*>/g, '')
    // Remove any extra whitespace and normalize line breaks
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/**
 * Learn component provides access to educational content in textbook and story formats.
 * Features real-time content updates via SSE, progress tracking, and format switching.
 * 
 * Key features:
 * - Dual format display (textbook/story)
 * - Progress tracking and section advancement
 * - Real-time content updates via SSE
 * - Markdown rendering with custom components
 * - Content polling for new materials
 * 
 * @param props - Component props
 * @param props.onBack - Callback function to navigate back to main menu
 */
const Learn = ({ onBack }: { onBack: () => void }) => {
  const [contentItems, setContentItems] = useState<ContentItem[]>([])
  const [selectedContent, setSelectedContent] = useState<ContentItem | null>(null)
  const [currentContent, setCurrentContent] = useState<LearnContent | null>(null)
  const [currentSection, setCurrentSection] = useState(1)
  const [loading, setLoading] = useState(true)
  const [contentLoading, setContentLoading] = useState(false)
  const [selectedFormat, setSelectedFormat] = useState<'textbook' | 'story'>('textbook')
  const [availableFormats, setAvailableFormats] = useState<{textbook: boolean, story: boolean}>({textbook: true, story: false})
  const [formatProgress, setFormatProgress] = useState<{[contentId: string]: {textbook: {viewedSections: number, lastViewed: string | null, currentSection?: number}, story: {viewedSections: number, lastViewed: string | null, currentSection?: number}, lastUsedFormat?: string}}>({})
  const [formatTotals, setFormatTotals] = useState<{[contentId: string]: {textbook?: number, story?: number}}>({})

  // Load content items from backend - SIMPLE VERSION
  const loadContentItems = async () => {
    try {
      setLoading(true)
      const items = await fetchContentItems()
      setContentItems(items)
    } catch (error) {
      // Error loading content items
    } finally {
      setLoading(false)
    }
  }

  // Format display name from filename
  const formatDisplayName = (name: string) => {
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase())
  }


  // API functions - connect to real backend
  const fetchContentItems = async (): Promise<ContentItem[]> => {
    try {
      const response = await fetch(`${API_BASE}/api/learn/list`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const items = await response.json()
      return items
    } catch (error) {
      // Error fetching content items
      // Return empty array on error to prevent app crash
      return []
    }
  }

  // SIMPLE: Load available formats and progress
  const loadAvailableFormats = async (contentId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/learn/${contentId}/formats`)
      if (response.ok) {
        const formats = await response.json()
        setAvailableFormats(formats)
        // Set default to textbook if available, otherwise story
        setSelectedFormat(formats.textbook ? 'textbook' : 'story')
      }
    } catch (error) {
      // Error loading formats
    }
  }

  // Load format-specific progress
  const loadFormatProgress = async (contentId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/learn/${contentId}/progress`)
      if (response.ok) {
        const progress = await response.json()
        setFormatProgress(prev => ({
          ...prev,
          [contentId]: progress
        }))
      }
    } catch (error) {
      // Error loading progress
      // Initialize with empty progress if loading fails
      setFormatProgress(prev => ({
        ...prev,
        [contentId]: {
          textbook: {viewedSections: 0, lastViewed: null, currentSection: 1},
          story: {viewedSections: 0, lastViewed: null, currentSection: 1},
          lastUsedFormat: 'textbook'
        }
      }))
    }
  }

  const loadContentDetail = async (item: ContentItem, format: 'textbook' | 'story' = selectedFormat) => {
    if (item.status === 'building') return
    
    try {
      setContentLoading(true)
      // Load content from real API with specified format
      const response = await fetch(`${API_BASE}/api/learn/${item.id}?format=${format}`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const content = await response.json()
      setCurrentContent(content)
      
      // Use the current section for this specific format
      const contentProgress = formatProgress[item.id]
      const lastUsedFormat = contentProgress?.lastUsedFormat
      const formatData = contentProgress?.[format]
      const currentFormatProgress = formatData?.viewedSections || 0
      const formatCurrentSection = formatData?.currentSection || 1
      const totalSections = content.total_sections
      
      // Store total sections for this format
      setFormatTotals(prev => ({
        ...prev,
        [item.id]: {
          ...prev[item.id],
          [format]: totalSections
        }
      }))
      
      // If this format is 100% completed, start from section 1
      // If this is the format the user was last using, go to their current section in this format
      // Otherwise go to the current section saved for this format
      if (currentFormatProgress >= totalSections) {
        setCurrentSection(1) // Start from beginning if this format is completed
      } else if (format === lastUsedFormat && formatCurrentSection) {
        setCurrentSection(formatCurrentSection) // Go to exactly where the user was in this format
      } else {
        setCurrentSection(formatCurrentSection || 1) // Go to saved section for this format
      }
    } catch (error) {
      // Error loading content
    } finally {
      setContentLoading(false)
    }
  }

  // SIMPLE: Select content
  const handleContentSelect = (item: ContentItem) => {
    setSelectedContent(item)
    setAvailableFormats({textbook: true, story: false}) // Reset
    
    // Load formats, progress, and content
    Promise.all([
      loadAvailableFormats(item.id),
      loadFormatProgress(item.id)
    ]).then(() => {
      // Use the last used format instead of defaulting to textbook
      const contentProgress = formatProgress[item.id]
      const lastUsedFormat = contentProgress?.lastUsedFormat || 'textbook'
      setSelectedFormat(lastUsedFormat as 'textbook' | 'story')
      loadContentDetail(item, lastUsedFormat as 'textbook' | 'story')
    })
  }

  const handleFormatChange = (format: 'textbook' | 'story') => {
    if (selectedContent && availableFormats[format]) {
      setSelectedFormat(format)
      loadContentDetail(selectedContent, format)
    }
  }

  const handleNextSection = () => {
    if (!currentContent) {
      // No currentContent available
      return
    }
    
    const totalSections = currentContent.total_sections
    
    if (!totalSections || totalSections <= 0) {
      // Invalid total_sections
      return
    }
    
    // Only allow advancing if we're not at the last section
    if (currentSection < totalSections) {
      // Advancing to next section
      setCurrentSection(currentSection + 1)
    } else {
      // Already at last section
    }
  }

  const handlePreviousSection = () => {
    if (currentSection > 1) {
      setCurrentSection(currentSection - 1)
    }
  }

  const updateProgress = async (contentId: string, viewedSections: number, format: 'textbook' | 'story', currentSection: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/learn/${contentId}/progress`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ viewedSections, format, currentSection })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const result = await response.json()
      // Updated progress
      return result
    } catch (error) {
      // Error updating progress
      return null
    }
  }

  // Color variations for content items with hex values for text
  const getContentColor = (index: number) => {
    const colors = [
      { bg: 'from-blue-500 to-blue-600', border: 'border-blue-200', hover: 'hover:border-blue-300', text: 'text-blue-600', hexColor: '#1d4ed8' },
      { bg: 'from-indigo-500 to-indigo-600', border: 'border-indigo-200', hover: 'hover:border-indigo-300', text: 'text-indigo-600', hexColor: '#4338ca' },
      { bg: 'from-purple-500 to-purple-600', border: 'border-purple-200', hover: 'hover:border-purple-300', text: 'text-purple-600', hexColor: '#7c3aed' },
      { bg: 'from-cyan-500 to-cyan-600', border: 'border-cyan-200', hover: 'hover:border-cyan-300', text: 'text-cyan-600', hexColor: '#0891b2' },
      { bg: 'from-sky-500 to-sky-600', border: 'border-sky-200', hover: 'hover:border-sky-300', text: 'text-sky-600', hexColor: '#0284c7' }
    ]
    return colors[index % colors.length]
  }

  // Progress calculation based on maximum completion between formats using real totals
  const getProgressPercentage = (item: ContentItem, formatProgressData: any, formatTotalsData: any) => {
    const contentProgress = formatProgressData[item.id]
    const contentTotals = formatTotalsData[item.id]
    
    if (!contentProgress) {
      // Fallback to original calculation if no format progress data
      if (!item.totalSections) return 0
      const percentage = Math.round(((item.viewedSections || 0) / item.totalSections) * 100)
      return Math.min(percentage, 100)
    }
    
    let maxPercentage = 0
    
    // Calculate textbook percentage using real total from formatTotals
    const textbookProgress = contentProgress.textbook || { viewedSections: 0 }
    if (contentTotals?.textbook && textbookProgress.viewedSections > 0) {
      const textbookPercentage = Math.round((textbookProgress.viewedSections / contentTotals.textbook) * 100)
      maxPercentage = Math.max(maxPercentage, textbookPercentage)
    }
    
    // Calculate story percentage using real total from formatTotals
    const storyProgress = contentProgress.story || { viewedSections: 0 }
    if (contentTotals?.story && storyProgress.viewedSections > 0) {
      const storyPercentage = Math.round((storyProgress.viewedSections / contentTotals.story) * 100)
      maxPercentage = Math.max(maxPercentage, storyPercentage)
    }
    
    // Safety cap: never exceed 100%
    return Math.min(maxPercentage, 100)
  }

  // REMOVED: Complex animation system replaced with simple CSS-based approach

  // SIMPLE: Load data once on mount
  useEffect(() => {
    loadContentItems()
  }, [])

  // SSE: Listen for real-time content updates
  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE}/api/events/stream`)
    
    eventSource.onopen = () => {
      // SSE connection opened
    }
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        // SSE event received
        
        // Handle different event types
        switch (data.type) {
          case 'connected':
            // SSE connected successfully
            break
            
          case 'heartbeat':
            // Heartbeat to keep connection alive - no action needed
            break
            
          case 'content_added':
          case 'processing_started':
          case 'processing_completed':
          case 'processing_failed':
            // Reload content items when any content changes
            // Reloading content due to event
            loadContentItems()
            break
            
          default:
            // Unknown SSE event type
        }
      } catch (error) {
        // Error parsing SSE event
      }
    }
    
    eventSource.onerror = (error) => {
      // SSE connection error
    }
    
    // Cleanup on unmount
    return () => {
      // SSE connection closed
      eventSource.close()
    }
  }, [])

  // SIMPLE: Update progress when section changes or when content loads (including section 1)
  useEffect(() => {
    if (selectedContent && currentSection > 0 && currentContent) {
      const contentProgress = formatProgress[selectedContent.id]
      const currentFormatProgress = contentProgress?.[selectedFormat]?.viewedSections || 0
      const newViewedCount = Math.max(currentFormatProgress, currentSection)
      
      // Limit to total sections - prevent going beyond the end
      const maxSections = currentContent.total_sections || 10
      const limitedViewedCount = Math.min(newViewedCount, maxSections)
      
      // Only update if there's actually new progress and it's within bounds
      if (limitedViewedCount > currentFormatProgress && limitedViewedCount <= maxSections) {
        // Updating progress
        
        // Update API and local state - include current section
        updateProgress(selectedContent.id, limitedViewedCount, selectedFormat, currentSection).then((result) => {
          if (result) {
            // Update format progress state for this specific content
            setFormatProgress(prev => ({
              ...prev,
              [selectedContent.id]: {
                ...prev[selectedContent.id],
                [selectedFormat]: {
                  viewedSections: limitedViewedCount,
                  lastViewed: new Date().toISOString().split('T')[0],
                  currentSection: currentSection
                },
                lastUsedFormat: result.lastUsedFormat
              }
            }))
            
            // Update selected content state with combined progress
            setSelectedContent(prev => prev ? {
              ...prev,
              viewedSections: result.combinedProgress,
              lastViewed: new Date().toISOString().split('T')[0]
            } : prev)
            
            // Update main content items state with combined progress
            setContentItems(prev => prev.map(item => 
              item.id === selectedContent.id 
                ? { ...item, viewedSections: result.combinedProgress, lastViewed: new Date().toISOString().split('T')[0] }
                : item
            ))
          }
        })
      }
    }
  }, [currentSection, currentContent]) // Remove selectedFormat from dependencies to prevent updating progress just from format changes

  if (selectedContent && currentContent) {
    // Content reading view
    const currentSectionData = currentContent.sections.find(s => s.section_number === currentSection)
    const progress = currentSection / currentContent.total_sections * 100
    
    // Get the color scheme for this content (same as in main menu)
    const contentIndex = contentItems.findIndex(item => item.id === selectedContent.id)
    const colors = getContentColor(contentIndex >= 0 ? contentIndex : 0)
    
    // Extract hex colors for gradients
    const primaryColor = colors.bg.includes('blue') ? '#3b82f6' : 
                        colors.bg.includes('indigo') ? '#6366f1' :
                        colors.bg.includes('purple') ? '#8b5cf6' :
                        colors.bg.includes('cyan') ? '#06b6d4' : '#0ea5e9'
    
    const secondaryColor = colors.bg.includes('blue') ? '#2563eb' : 
                          colors.bg.includes('indigo') ? '#4f46e5' :
                          colors.bg.includes('purple') ? '#7c3aed' :
                          colors.bg.includes('cyan') ? '#0891b2' : '#0284c7'

    // DISEÑO C: CARD-BASED COHESIVO (Igual que el menú principal)
    return (
      <div className="min-h-full bg-app-bg">
        {/* Header como card flotante */}
        <div className="p-4">
          <div 
            className="rounded-2xl shadow-sm p-4 relative overflow-hidden"
            style={{
              background: `linear-gradient(to right, ${primaryColor}, ${secondaryColor})`
            }}
          >
            <div className="flex items-center justify-between relative z-10">
              <button
                onClick={() => {
                  setSelectedContent(null)
                  setCurrentContent(null)
                }}
                className="p-2 rounded-xl bg-white/20 hover:bg-white/30 transition-all duration-300 hover:-translate-y-0.5"
              >
                <ArrowLeft className="w-6 h-6 text-white" />
              </button>
              
              <div className="text-sm font-semibold text-white">
                {currentSection} of {currentContent.total_sections}
              </div>
            </div>

            {/* Progress integrado en header */}
            <div className="mt-4 bg-white/20 rounded-full h-2">
              <div 
                className="bg-white h-2 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Format tabs - modern tab style */}
        {(availableFormats.textbook && availableFormats.story) && (
          <div className="px-4 pb-4">
            <div className="bg-white rounded-2xl shadow-sm p-2 border border-gray-200">
              <div className="bg-gray-100 p-1 rounded-xl flex">
                <button
                  onClick={() => handleFormatChange('textbook')}
                  className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all duration-250 ${
                    selectedFormat === 'textbook'
                      ? 'bg-white shadow-sm'
                      : 'text-gray-600'
                  }`}
                  style={{
                    color: selectedFormat === 'textbook' ? primaryColor : undefined
                  }}
                >
                  Textbook
                </button>
                <button
                  onClick={() => handleFormatChange('story')}
                  className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all duration-250 ${
                    selectedFormat === 'story'
                      ? 'bg-white shadow-sm'
                      : 'text-gray-600'
                  }`}
                  style={{
                    color: selectedFormat === 'story' ? primaryColor : undefined
                  }}
                >
                  Story
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Content como card del menú principal */}
        <main className="px-4 pb-8">
          <h1 className="text-2xl font-bold text-gray-800 mb-6 px-2">
            {selectedContent.displayName}
          </h1>
          
          {contentLoading ? (
            <div className="bg-white rounded-2xl shadow-sm p-12 text-center border border-gray-200">
              <Loader2 className="w-8 h-8 animate-spin mx-auto" style={{ color: primaryColor }} />
            </div>
          ) : currentSectionData ? (
            <div className="space-y-4">
              {/* Content card sin fondo de progreso */}
              <div className="bg-white rounded-2xl shadow-sm p-6 border border-gray-200 hover:shadow-md transition-all duration-500">
                <div className="prose prose-lg max-w-none text-gray-700 leading-relaxed">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({children}) => <p className="mb-4">{children}</p>,
                      strong: ({children}) => <strong className="font-bold text-gray-900">{children}</strong>,
                      em: ({children}) => <em className="italic text-gray-600">{children}</em>,
                      code: ({children}) => <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-gray-800">{children}</code>,
                      h1: ({children}) => <h1 className="text-2xl font-bold mb-4 mt-6 text-gray-900">{children}</h1>,
                      h2: ({children}) => <h2 className="text-xl font-semibold mb-3 mt-5 text-gray-900">{children}</h2>,
                      h3: ({children}) => <h3 className="text-lg font-medium mb-2 mt-4 text-gray-900">{children}</h3>,
                      ul: ({children}) => <ul className="list-disc pl-6 mb-4 space-y-1">{children}</ul>,
                      ol: ({children}) => <ol className="list-decimal pl-6 mb-4 space-y-1">{children}</ol>,
                      li: ({children}) => <li className="text-gray-700">{children}</li>,
                      blockquote: ({children}) => <blockquote className="border-l-4 border-gray-300 pl-4 py-2 mb-4 bg-gray-50 rounded text-gray-700">{children}</blockquote>,
                      table: ({children}) => <table className="min-w-full divide-y divide-gray-200 my-4 border border-gray-300 rounded-lg overflow-hidden">{children}</table>,
                      thead: ({children}) => <thead className="bg-gray-50">{children}</thead>,
                      tbody: ({children}) => <tbody className="bg-white divide-y divide-gray-200">{children}</tbody>,
                      tr: ({children}) => <tr>{children}</tr>,
                      th: ({children}) => <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-r border-gray-300 last:border-r-0">{children}</th>,
                      td: ({children}) => <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-900 border-r border-gray-300 last:border-r-0">{children}</td>
                    }}
                  >
                    {parseHtmlToMarkdown(currentSectionData.content)}
                  </ReactMarkdown>
                </div>
              </div>

              {/* Navigation cards */}
              <div className="flex justify-between items-center gap-4 mb-6">
                <button
                  onClick={handlePreviousSection}
                  disabled={currentSection === 1}
                  className={`px-6 py-3 bg-white rounded-2xl shadow-sm border transition-all duration-500 font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-md hover:-translate-y-0.5`}
                  style={{ 
                    borderColor: colors.border.includes('border-') ? colors.border.replace('border-', '') : primaryColor + '40',
                    color: primaryColor 
                  }}
                >
                  Previous
                </button>

                <button
                  onClick={handleNextSection}
                  disabled={!currentContent || !currentContent.total_sections || currentSection >= currentContent.total_sections}
                  className="px-6 py-3 text-white rounded-2xl shadow-sm hover:shadow-md hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-500 flex items-center space-x-2 font-medium"
                  style={{
                    background: `linear-gradient(to right, ${primaryColor}, ${secondaryColor})`
                  }}
                >
                  <span>
                    {currentContent && currentContent.total_sections && currentSection < currentContent.total_sections ? 'Next' : 'Completed!'}
                  </span>
                </button>
              </div>
            </div>
          ) : null}
        </main>
      </div>
    )
  }

  // Topic selection view
  return (
    <div className="min-h-full bg-app-bg">
      {/* Header */}
      <header className="grid grid-cols-3 items-center p-4 bg-card-bg shadow-sm">
        <button
          onClick={onBack}
          className="p-2 text-learn-blue hover:text-learn-blue-dark transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        
        <h1 className="text-xl font-semibold text-gray-800 text-center">Learn</h1>
        
        <div></div>
      </header>

      {/* Content */}
      <main className="p-6">
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-learn-blue" />
          </div>
        ) : (
          <div className="space-y-4">

            {contentItems.map((item, index) => {
              const colors = getContentColor(index)
              const progressPercentage = getProgressPercentage(item, formatProgress, formatTotals)
              
              return (
                <div key={item.id} className="relative">
                  <button
                    onClick={() => item.status === 'available' && handleContentSelect(item)}
                    disabled={item.status === 'building'}
                    className={`
                      w-full p-6 rounded-2xl shadow-sm transition-all duration-500 text-left relative overflow-hidden liquid-fill-card
                      ${item.status === 'available' 
                        ? `bg-white hover:shadow-md hover:-translate-y-0.5 border ${colors.border} ${colors.hover}`
                        : 'bg-gray-50 border border-gray-200 cursor-not-allowed opacity-75'
                      }
                    `}
                  >
                    {/* SIMPLE: CSS-based progress background */}
                    {item.status === 'available' && (item.viewedSections || 0) > 0 && (
                      <div 
                        className="absolute inset-0 rounded-2xl transition-all duration-1000 ease-out"
                        style={{
                          background: `linear-gradient(to right, ${
                            colors.bg.includes('blue') ? '#3b82f6' : 
                            colors.bg.includes('indigo') ? '#6366f1' :
                            colors.bg.includes('purple') ? '#8b5cf6' :
                            colors.bg.includes('cyan') ? '#06b6d4' : '#0ea5e9'
                          } 0%, ${
                            colors.bg.includes('blue') ? '#2563eb' : 
                            colors.bg.includes('indigo') ? '#4f46e5' :
                            colors.bg.includes('purple') ? '#7c3aed' :
                            colors.bg.includes('cyan') ? '#0891b2' : '#0284c7'
                          } 100%)`,
                          clipPath: `inset(0 ${100 - progressPercentage}% 0 0)`,
                          opacity: 0.8
                        }}
                      />
                    )}

                    {/* Base content layer (theme color) */}
                    <div className="flex items-center justify-between relative z-10">
                      <div className="flex-1">
                        <h3 
                          className="font-semibold text-lg mb-1"
                          style={{ color: colors.hexColor }}
                        >
                          {item.displayName}
                        </h3>
                        
                        {item.status === 'building' ? (
                          <div className="flex items-center space-x-2 text-orange-600">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span className="text-sm font-medium">Gemma 3n is generating...</span>
                          </div>
                        ) : null}
                      </div>

                      {/* Progress indicator */}
                      {item.status === 'available' && (
                        <div className="text-right">
                          {(item.viewedSections || 0) > 0 ? (
                            <div 
                              className="text-2xl font-bold"
                              style={{ color: colors.hexColor }}
                            >
                              {progressPercentage}%
                            </div>
                          ) : (
                            <div className="text-gray-400 text-lg">
                              New
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* White text masking layer - uses same coordinates as progress bar */}
                    {item.status === 'available' && (item.viewedSections || 0) > 0 && (
                      <div 
                        className="absolute inset-0 rounded-2xl transition-all duration-1000 ease-out z-20"
                        style={{
                          maskImage: `linear-gradient(to right, black 0%, black ${progressPercentage}%, transparent ${progressPercentage}%, transparent 100%)`,
                          WebkitMaskImage: `linear-gradient(to right, black 0%, black ${progressPercentage}%, transparent ${progressPercentage}%, transparent 100%)`
                        }}
                      >
                        {/* Recreate exact button layout with same padding */}
                        <div className="p-6 flex items-center justify-between h-full">
                          <div className="flex-1">
                            <h3 className="font-semibold text-lg mb-1 text-white">
                              {item.displayName}
                            </h3>
                          </div>
                          <div className="text-right">
                            <div className="text-2xl font-bold text-white">
                              {progressPercentage}%
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </button>
                </div>
              )
            })}

            {contentItems.length === 0 && !loading && (
              <div className="text-center py-12 text-gray-500">
                <div className="w-12 h-12 mx-auto mb-4 opacity-50 bg-gray-200 rounded-2xl flex items-center justify-center">
                  <ArrowLeft className="w-6 h-6" />
                </div>
                <p>No content available yet. Add content to the backend to get started!</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default Learn