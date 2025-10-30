console.log("e-Courts Captcha Solver: Script Injected (v5 - Observer+Canvas)");

const API_URL = "http://127.0.0.1:5000/solve_captcha";
const CAPTCHA_INPUT_ID = "captcha";
const CAPTCHA_IMAGE_ID = "captcha_image";

let solving = false; // Flag to prevent multiple runs

/**
 * Reads the pixels from the on-page image element and converts them to a Blob.
 * @param {HTMLImageElement} imgElement The <img> tag on the page.
 * @returns {Promise<Blob>} A promise that resolves with the image data.
 */
function getImageBlobFromCanvas(imgElement) {
  return new Promise((resolve, reject) => {
    try {
      // 1. Create a canvas element in memory
      const canvas = document.createElement("canvas");

      // 2. Set canvas dimensions to match the *actual* image size
      canvas.width = imgElement.naturalWidth;
      canvas.height = imgElement.naturalHeight;

      // 3. Draw the visible image onto the canvas
      const ctx = canvas.getContext("2d");
      // This line is important: it prevents cross-origin errors
      // We can't do this, but the image *should* be same-origin.
      // imgElement.crossOrigin = "Anonymous";
      ctx.drawImage(imgElement, 0, 0);

      // 4. Get the image data from the canvas as a Blob
      canvas.toBlob((blob) => {
        if (blob && blob.size > 0) {
          resolve(blob);
        } else {
          reject(
            new Error(
              "Canvas toBlob failed or created empty blob. Image might be cross-origin or invalid."
            )
          );
        }
      }, "image/png");
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * The main function to solve the captcha.
 */
async function solveAndFillCaptcha(imgElement) {
  if (solving) return; // Don't run if we are already solving

  // Wait for the 'load' event to ensure the image is fully drawn
  if (!imgElement.complete || imgElement.naturalWidth === 0) {
    console.log("e-Courts Solver: Image not complete, waiting for load...");
    await new Promise((resolve, reject) => {
      imgElement.onload = resolve;
      imgElement.onerror = () =>
        reject(new Error("Image failed to load (onerror event)"));
    });
    console.log("e-Courts Solver: Image finished loading.");
  }

  solving = true; // Set the flag
  console.log("e-Courts Solver: Reading pixels from canvas...");

  try {
    const imageBlob = await getImageBlobFromCanvas(imgElement);

    console.log("e-Courts Solver: Sending image to API server...");
    const formData = new FormData();
    formData.append("file", imageBlob, "captcha.png");

    const apiResponse = await fetch(API_URL, {
      method: "POST",
      body: formData,
    });

    if (!apiResponse.ok)
      throw new Error(`API server error: ${apiResponse.statusText}`);

    const data = await apiResponse.json();
    if (data.error) throw new Error(`API returned an error: ${data.error}`);

    const solvedText = data.text;
    console.log(`e-Courts Solver: Solved text: ${solvedText}`);

    const captchaInput = document.getElementById(CAPTCHA_INPUT_ID);
    if (captchaInput) {
      captchaInput.value = solvedText;
      console.log("e-Courts Solver: Captcha field filled!");
    }
  } catch (error) {
    console.error("e-Courts Solver: CRITICAL ERROR:", error.message);
  } finally {
    solving = false; // Unset the flag
  }
}

// --- The MutationObserver Setup ---

// Find the target node to observe
const targetNode = document.getElementById(CAPTCHA_IMAGE_ID);

if (targetNode) {
  // 1. Solve the captcha that's loaded first
  // We add a delay to let the page's own scripts run first
  setTimeout(() => {
    solveAndFillCaptcha(targetNode);
  }, 500); // 500ms delay

  // 2. Create an observer to watch for changes
  const config = { attributes: true, attributeFilter: ["src"] };

  // Callback function to execute when mutations are observed
  const callback = (mutationsList, observer) => {
    for (const mutation of mutationsList) {
      if (mutation.type === "attributes" && mutation.attributeName === "src") {
        console.log(
          "e-Courts Solver: New captcha image detected! Re-solving..."
        );
        // The 'src' changed, so re-run the solver
        solveAndFillCaptcha(targetNode);
      }
    }
  };

  const observer = new MutationObserver(callback);
  observer.observe(targetNode, config);
} else {
  console.error(
    "e-Courts Solver: Could not find target captcha image to observe."
  );
}
