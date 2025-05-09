for file in *.yml; do
    echo "Testing $file"
    python3 check.py "$file"
done