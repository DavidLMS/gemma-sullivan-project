import { ArrowRight } from 'lucide-react'

interface WelcomeProps {
  onGetStarted: () => void
}

const Welcome = ({ onGetStarted }: WelcomeProps) => {
  return (
    <div className="min-h-screen bg-app-bg flex flex-col">
      {/* Centered Logo and Title */}
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <img 
            src="/logo.svg" 
            alt="Gemma Logo" 
            className="w-48 h-48 mx-auto mb-8 object-contain"
          />
          <h1 className="text-3xl font-bold text-gray-800">
            Gemma Sullivan Project
          </h1>
        </div>
      </div>

      {/* Bottom Button */}
      <div className="p-6">
        <button
          onClick={onGetStarted}
          className="w-full bg-gradient-to-r from-primary to-primary-dark hover:from-primary-dark hover:to-gray-800 text-white font-semibold py-4 px-6 rounded-xl transition-all duration-300 shadow-md hover:shadow-lg hover:-translate-y-0.5 flex items-center justify-center space-x-2"
        >
          <span>Get Started</span>
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}

export default Welcome