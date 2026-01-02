module.exports = {
  // Disable postcss-import to prevent it from processing JS files
  plugins: [
    require('tailwindcss')({
      config: './tailwind.config.cjs'
    }),
    require('autoprefixer')()
  ]
}