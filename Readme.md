# Install

Create a virtual env, and install the dependecies in `requirements.txt`
Then install `vercel` used for deploying with the following command: `npm install vercel`

# API usage

By default the server use the addess `127.0.0.1:5000`

## / 

Return the frontend for a interactive usage

## /upload

Upload the pdf following the attached options and return the adjusted pdf.

### Options

- **Placemente**: where put the blank space
  - **default**: left
  - top, bottom, left, right 
- **style**: what kind of background use for the blank space
  - **default**: lines
  - lines, dots, squares
- **spacing**: spacing between lines/dots/squares
  - **default**: 20
  - an integer

#### Curl example

```bash
 curl -X POST "http://localhost:5000/upload" \
     -F "pdf=@/path/to/pdf" \
     -F "placement=right" \
     -F "style=lines" \
     -F "spacing=30" \
     -o "output.pdf" 
```