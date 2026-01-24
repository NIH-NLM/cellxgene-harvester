#!/bin/bash
#!/bin/bash

# Create environment from file (handles everything)
conda env create -f environment.yml

echo ""
echo "Setup complete!"
echo "To activate, run:"
echo "  conda activate cellxgene"
