document.addEventListener("alpine:init", () => {
  Alpine.data('prediction', () => {
    return {
      show: false,
      predict: false,


    }
  })
})