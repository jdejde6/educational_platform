"use client";

import React, { useState } from "react";
import MDEditor from "@uiw/react-md-editor";
import "@uiw/react-md-editor/markdown-editor.css";
// import "@uiw/react-md-editor/github-markdown.css"; // This line caused an error, will try importing github-markdown-css directly
import "github-markdown-css/github-markdown.css"; // Attempting to import the specific package

// For LaTeX support
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css"; // KaTeX CSS

const MarkdownEditorTestPage = () => {
  const [value, setValue] = useState(
`**Hello world!!!**

Let's test LaTeX:

Inline math: $E = mc^2$

Display math (Pandoc style):

$$
\int_0^\infty x^2 e^{-x} dx = 2
$$

Display math (GitLab/GitHub style):

\
\
\
math
\frac{d}{dx} \left( \int_0^x f(u) du \right) = f(x)
\
\
\

Another inline example: $\alpha + \beta = \gamma$.

More complex display equation:

$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$
`
  );

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Markdown Editor with LaTeX Test</h1>
      <div data-color-mode="light"> {/* Or "dark" based on your theme preference */}
        <MDEditor
          value={value}
          onChange={(val) => setValue(val || "")}
          height={500}
          previewOptions={{
            remarkPlugins: [remarkMath],
            rehypePlugins: [rehypeKatex],
          }}
        />
      </div>
      <h2 className="text-xl font-semibold mt-6 mb-2">Live Preview (within editor is already using KaTeX if configured)</h2>
      
      <h2 className="text-xl font-semibold mt-6 mb-2">Standalone MDEditor.Markdown Preview:</h2>
      {/* Apply the github-markdown-body class for styling the preview */}
      <div className="markdown-body prose lg:prose-xl p-4 border rounded" data-color-mode="light">
        <MDEditor.Markdown 
            source={value} 
            remarkPlugins={[remarkMath]} 
            rehypePlugins={[rehypeKatex]} 
        />
      </div>
    </div>
  );
};

export default MarkdownEditorTestPage;

