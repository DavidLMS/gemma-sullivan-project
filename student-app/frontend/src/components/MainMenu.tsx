import { BookOpen, Target, Beaker, Search, ChevronRight } from 'lucide-react'

interface MainMenuProps {
  onNavigate: (view: 'learn' | 'practice' | 'experiment' | 'discover') => void
}

/**
 * Main navigation menu component with bento-style grid layout.
 * Provides access to all major learning modes with visual 3D effects.
 * 
 * Navigation options:
 * - Learn: Educational content (textbooks/stories)
 * - Practice: Interactive questions
 * - Experiment: Challenge-based learning
 * - Discover: Camera-based investigation
 * 
 * @param props - Component props
 * @param props.onNavigate - Callback function to navigate to different views
 */
const MainMenu = ({ onNavigate }: MainMenuProps) => {
  const handleLearn = () => onNavigate('learn')
  const handlePractice = () => onNavigate('practice')
  const handleExperiment = () => onNavigate('experiment')
  const handleDiscover = () => onNavigate('discover')

  return (
    <div className="flex flex-col p-4 pt-6 space-y-6">
      {/* Bento Grid Layout con elementos 3D y swipe gestures */}
      
      {/* Learn - Elemento principal con perspectiva 3D */}
      <div className="relative">
        <button
          onClick={handleLearn}
          className="group w-full h-32 bg-gradient-to-br from-blue-500 to-blue-600 rounded-3xl shadow-lg hover:shadow-xl transition-all duration-500 transform hover:scale-[1.02] hover:-translate-y-1 overflow-hidden relative"
        >
          {/* Efecto de profundidad con múltiples capas */}
          <div className="absolute inset-0 bg-gradient-to-tr from-white/20 to-transparent"></div>
          <div className="absolute bottom-0 left-0 w-full h-1/2 bg-gradient-to-t from-black/10 to-transparent"></div>
          
          {/* Contenido principal */}
          <div className="relative z-10 h-full flex items-center px-6">
            <div className="flex items-center space-x-4">
              {/* Icono con efecto neumorphic */}
              <div className="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center shadow-inner">
                <BookOpen className="w-6 h-6 text-white" />
              </div>
              <div className="text-left">
                <h2 className="text-xl font-bold text-white">Learn</h2>
                <p className="text-blue-100 text-sm">Read & understand</p>
              </div>
            </div>
            {/* Indicador de swipe */}
            <div className="ml-auto">
              <ChevronRight className="w-6 h-6 text-white/60 group-hover:translate-x-1 transition-transform duration-300" />
            </div>
          </div>

          {/* Partículas flotantes decorativas */}
          <div className="absolute top-4 right-6 w-2 h-2 bg-white/30 rounded-full animate-pulse"></div>
          <div className="absolute top-8 right-12 w-1 h-1 bg-white/20 rounded-full animate-pulse delay-300"></div>
        </button>
      </div>

      {/* Grid 2x2 para Practice y Experiment */}
      <div className="grid grid-cols-2 gap-4">
        {/* Practice - Formato hexagonal simulado */}
        <button
          onClick={handlePractice}
          className="group h-28 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-500 transform hover:scale-105 hover:rotate-1 overflow-hidden relative"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent"></div>
          
          <div className="relative z-10 h-full flex flex-col items-center justify-center p-4">
            {/* Icono con animación kinética */}
            <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center mb-2 group-hover:rotate-12 transition-transform duration-300">
              <Target className="w-5 h-5 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-white">Practice</h3>
            <p className="text-green-100 text-xs text-center">Test yourself</p>
          </div>

          {/* Efecto de ondas al hover */}
          <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-white/10 rounded-full group-hover:scale-150 group-hover:opacity-0 transition-all duration-500"></div>
        </button>

        {/* Experiment - Con efecto de vidrio esmerilado */}
        <button
          onClick={handleExperiment}
          className="group h-28 bg-gradient-to-br from-orange-500 to-amber-600 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-500 transform hover:scale-105 hover:-rotate-1 overflow-hidden relative"
        >
          <div className="absolute inset-0 bg-gradient-to-tl from-white/10 to-transparent"></div>
          
          <div className="relative z-10 h-full flex flex-col items-center justify-center p-4">
            {/* Icono con efecto de pulsación */}
            <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center mb-2 group-hover:animate-pulse">
              <Beaker className="w-5 h-5 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-white">Experiment</h3>
            <p className="text-orange-100 text-xs text-center">Create & build</p>
          </div>

          {/* Elementos decorativos flotantes */}
          <div className="absolute top-2 left-3 w-1.5 h-1.5 bg-white/20 rounded-full animate-bounce delay-100"></div>
          <div className="absolute bottom-3 right-2 w-1 h-1 bg-white/30 rounded-full animate-bounce delay-500"></div>
        </button>
      </div>

      {/* Discover - Estilo minimalista flotante */}
      <div className="flex flex-col items-center space-y-4 pt-4">
        <p className="text-gray-500 text-sm font-light tracking-wide">
          Only want to look around?
        </p>
        
        {/* Botón con efecto magnético */}
        <button
          onClick={handleDiscover}
          className="group relative bg-white border border-gray-200 hover:border-primary/50 px-8 py-3 rounded-full shadow-sm hover:shadow-lg transition-all duration-300 transform hover:-translate-y-0.5"
        >
          {/* Efecto de halo al hover */}
          <div className="absolute inset-0 bg-primary/5 rounded-full scale-0 group-hover:scale-110 transition-transform duration-300"></div>
          
          <div className="relative flex items-center space-x-2">
            <Search className="w-4 h-4 text-primary group-hover:rotate-12 transition-transform duration-300" />
            <span className="text-primary font-medium">Discover</span>
          </div>

          {/* Indicador de interacción */}
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300 animate-ping"></div>
        </button>
      </div>
    </div>
  )
}

export default MainMenu