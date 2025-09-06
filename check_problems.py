#!/usr/bin/env python3
"""
Script to check all ch*.tex files for missing components in problem solutions:
- Missing "Strategy" part
- Missing "Solution" part  
- Missing "\qed" at the end of solutions
- Extra "\qed" commands (multiple \qed in one solution or \qed without solution)

The script can also automatically fix issues:
- Add missing \qed or remove extra \qed commands
- Wrap "Importance" sections with \begin{importance} and \end{importance}

Usage: python check_problems.py [directory] [--fix] [--detailed]
If no directory is specified, defaults to 'apostol'
Use --fix flag to automatically fix issues
Use --detailed flag to show detailed report of all problems
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class ProblemChecker:
    def __init__(self, directory: str = "apostol", auto_fix: bool = False):
        self.directory = Path(directory)
        self.issues = []
        self.auto_fix = auto_fix
        self.fixes_applied = 0
        
    def find_chapter_files(self) -> List[Path]:
        """Find all ch*.tex files in the directory."""
        chapter_files = []
        if self.directory.exists():
            for file_path in self.directory.glob("ch*.tex"):
                chapter_files.append(file_path)
        return sorted(chapter_files)
    
    def extract_problems(self, file_path: Path) -> List[Dict]:
        """Extract all problems from a chapter file."""
        problems = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return problems
        
        # Find all problembox sections
        problembox_pattern = r'\\begin\{problembox\}\[([^\]]+)\](.*?)\\end\{problembox\}'
        problembox_matches = re.finditer(problembox_pattern, content, re.DOTALL)
        
        for match in problembox_matches:
            problem_title = match.group(1).strip()
            problem_content = match.group(2).strip()
            
            # Find the end position of this problembox
            problembox_end = match.end()
            
            # Look for Strategy and Solution after this problembox
            remaining_content = content[problembox_end:]
            
            # Find the next problembox or end of file to limit our search
            next_problembox = re.search(r'\\begin\{problembox\}', remaining_content)
            if next_problembox:
                search_content = remaining_content[:next_problembox.start()]
            else:
                search_content = remaining_content
            
            # Check for Strategy
            strategy_match = re.search(r'\\textbf\{Strategy:\}', search_content)
            has_strategy = strategy_match is not None
            
            # Check for Solution
            solution_match = re.search(r'\\textbf\{Solution:\}', search_content)
            has_solution = solution_match is not None
            
            # Check for \qed - look for it after the solution
            has_qed = False
            qed_count = 0
            extra_qed_issues = []
            
            if solution_match:
                # Look for \qed after the solution
                solution_end = solution_match.end()
                after_solution = search_content[solution_end:]
                qed_matches = list(re.finditer(r'\\qed', after_solution))
                qed_count = len(qed_matches)
                has_qed = qed_count > 0
                
                # Check for extra \qed issues
                if qed_count > 1:
                    extra_qed_issues.append(f"Multiple \\qed ({qed_count} found)")
                elif qed_count == 0:
                    extra_qed_issues.append("Missing \\qed")
            else:
                # Check if there's a \qed without a solution
                qed_matches = list(re.finditer(r'\\qed', search_content))
                if qed_matches:
                    extra_qed_issues.append(f"\\qed without Solution ({len(qed_matches)} found)")
            
            problems.append({
                'title': problem_title,
                'has_strategy': has_strategy,
                'has_solution': has_solution,
                'has_qed': has_qed,
                'qed_count': qed_count,
                'extra_qed_issues': extra_qed_issues,
                'file': file_path.name
            })
        
        return problems
    
    def fix_missing_qed(self, file_path: Path) -> int:
        """Fix missing \qed in a file and return number of fixes applied."""
        fixes_applied = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return 0
        
        # Find all problembox sections
        problembox_pattern = r'\\begin\{problembox\}\[([^\]]+)\](.*?)\\end\{problembox\}'
        problembox_matches = list(re.finditer(problembox_pattern, content, re.DOTALL))
        
        # Process from end to beginning to avoid offset issues
        for match in reversed(problembox_matches):
            problem_title = match.group(1).strip()
            problembox_end = match.end()
            
            # Look for content after this problembox
            remaining_content = content[problembox_end:]
            
            # Find the next problembox or end of file to limit our search
            next_problembox = re.search(r'\\begin\{problembox\}', remaining_content)
            if next_problembox:
                search_content = remaining_content[:next_problembox.start()]
            else:
                search_content = remaining_content
            
            # Check for Solution
            solution_match = re.search(r'\\textbf\{Solution:\}', search_content)
            if solution_match:
                # Look for \qed after the solution
                solution_end = solution_match.end()
                after_solution = search_content[solution_end:]
                qed_match = re.search(r'\\qed', after_solution)
                
                if not qed_match:
                    # Find the end of the solution content (before next problembox or end)
                    # Look for the last non-whitespace character before the next problembox
                    solution_content = after_solution.rstrip()
                    
                    if solution_content:
                        # Find the position in the original content where we need to add \qed
                        solution_start_in_file = problembox_end + solution_match.end()
                        solution_end_in_file = solution_start_in_file + len(solution_content)
                        
                        # Add \qed at the end of the solution
                        new_content = (content[:solution_end_in_file] + 
                                     '\\qed' + 
                                     content[solution_end_in_file:])
                        
                        content = new_content
                        fixes_applied += 1
                        print(f"  ✅ Added \\qed to problem: {problem_title}")
        
        # Write the fixed content back to file
        if fixes_applied > 0:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  📝 Updated {file_path.name} with {fixes_applied} fixes")
            except Exception as e:
                print(f"  ❌ Error writing {file_path}: {e}")
                return 0
        
        return fixes_applied
    
    def fix_extra_qed(self, file_path: Path) -> int:
        """Fix extra \qed issues in a file and return number of fixes applied."""
        fixes_applied = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return 0
        
        # Find all problembox sections
        problembox_pattern = r'\\begin\{problembox\}\[([^\]]+)\](.*?)\\end\{problembox\}'
        problembox_matches = list(re.finditer(problembox_pattern, content, re.DOTALL))
        
        # Process from end to beginning to avoid offset issues
        for match in reversed(problembox_matches):
            problem_title = match.group(1).strip()
            problembox_end = match.end()
            
            # Look for content after this problembox
            remaining_content = content[problembox_end:]
            
            # Find the next problembox or end of file to limit our search
            next_problembox = re.search(r'\\begin\{problembox\}', remaining_content)
            if next_problembox:
                search_content = remaining_content[:next_problembox.start()]
            else:
                search_content = remaining_content
            
            # Check for Solution
            solution_match = re.search(r'\\textbf\{Solution:\}', search_content)
            
            if solution_match:
                # Look for \qed after the solution
                solution_end = solution_match.end()
                after_solution = search_content[solution_end:]
                qed_matches = list(re.finditer(r'\\qed', after_solution))
                
                if len(qed_matches) > 1:
                    # Multiple \qed found - keep only the first one
                    first_qed_end = qed_matches[0].end()
                    # Remove all \qed after the first one
                    content_to_fix = after_solution[first_qed_end:]
                    fixed_content = re.sub(r'\\qed', '', content_to_fix)
                    
                    # Calculate positions in the original content
                    solution_start_in_file = problembox_end + solution_match.end()
                    first_qed_end_in_file = solution_start_in_file + first_qed_end
                    content_end_in_file = solution_start_in_file + len(after_solution)
                    
                    # Replace the content
                    new_content = (content[:first_qed_end_in_file] + 
                                 fixed_content + 
                                 content[content_end_in_file:])
                    
                    content = new_content
                    fixes_applied += len(qed_matches) - 1
                    print(f"  ✅ Removed {len(qed_matches) - 1} extra \\qed from problem: {problem_title}")
            
            else:
                # No solution found - remove any \qed
                qed_matches = list(re.finditer(r'\\qed', search_content))
                if qed_matches:
                    # Remove all \qed from this section
                    fixed_content = re.sub(r'\\qed', '', search_content)
                    
                    # Calculate positions in the original content
                    section_start_in_file = problembox_end
                    section_end_in_file = problembox_end + len(search_content)
                    
                    # Replace the content
                    new_content = (content[:section_start_in_file] + 
                                 fixed_content + 
                                 content[section_end_in_file:])
                    
                    content = new_content
                    fixes_applied += len(qed_matches)
                    print(f"  ✅ Removed {len(qed_matches)} \\qed without Solution from problem: {problem_title}")
        
        # Write the fixed content back to file
        if fixes_applied > 0:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  📝 Updated {file_path.name} with {fixes_applied} extra \\qed fixes")
            except Exception as e:
                print(f"  ❌ Error writing {file_path}: {e}")
                return 0
        
        return fixes_applied
    
    def fix_importance_sections(self, file_path: Path) -> int:
        """Fix Importance sections by wrapping them with \\begin{importance} and \\end{importance}."""
        fixes_applied = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return 0
        
        # Find all problembox sections
        problembox_pattern = r'\\begin\{problembox\}\[([^\]]+)\](.*?)\\end\{problembox\}'
        problembox_matches = list(re.finditer(problembox_pattern, content, re.DOTALL))
        
        # Process from end to beginning to avoid offset issues
        for match in reversed(problembox_matches):
            problem_title = match.group(1).strip()
            problembox_end = match.end()
            
            # Look for content after this problembox
            remaining_content = content[problembox_end:]
            
            # Find the next problembox or end of file to limit our search
            next_problembox = re.search(r'\\begin\{problembox\}', remaining_content)
            if next_problembox:
                search_content = remaining_content[:next_problembox.start()]
            else:
                search_content = remaining_content
            
            # Look for Importance sections that are not already wrapped
            importance_pattern = r'\\textbf\{Importance:\}(.*?)(?=\\textbf\{|\\begin\{|\\end\{|$)'
            importance_matches = list(re.finditer(importance_pattern, search_content, re.DOTALL))
            
            for importance_match in reversed(importance_matches):
                importance_start = importance_match.start()
                importance_end = importance_match.end()
                importance_content = importance_match.group(1).strip()
                
                # Check if this Importance section is already wrapped
                # Look backwards from the start to see if there's a \begin{importance}
                before_importance = search_content[:importance_start]
                if '\\begin{importance}' not in before_importance[-50:]:  # Check last 50 chars
                    # Look forwards from the end to see if there's an \end{importance}
                    after_importance = search_content[importance_end:]
                    if '\\end{importance}' not in after_importance[:50]:  # Check first 50 chars
                        # This Importance section needs to be wrapped
                        
                        # Calculate positions in the original content
                        section_start_in_file = problembox_end + importance_start
                        section_end_in_file = problembox_end + importance_end
                        
                        # Wrap the Importance section
                        wrapped_content = ('\\begin{importance}\n' + 
                                         '\\textbf{Importance:}' + importance_content + 
                                         '\n\\end{importance}')
                        
                        # Replace the content
                        new_content = (content[:section_start_in_file] + 
                                     wrapped_content + 
                                     content[section_end_in_file:])
                        
                        content = new_content
                        fixes_applied += 1
                        print(f"  ✅ Wrapped Importance section in problem: {problem_title}")
        
        # Write the fixed content back to file
        if fixes_applied > 0:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  📝 Updated {file_path.name} with {fixes_applied} Importance section fixes")
            except Exception as e:
                print(f"  ❌ Error writing {file_path}: {e}")
                return 0
        
        return fixes_applied
    
    def check_file(self, file_path: Path) -> List[Dict]:
        """Check a single file for issues."""
        problems = self.extract_problems(file_path)
        file_issues = []
        
        for problem in problems:
            issues = []
            if not problem['has_strategy']:
                issues.append("Missing Strategy")
            if not problem['has_solution']:
                issues.append("Missing Solution")
            if problem['has_solution'] and not problem['has_qed']:
                issues.append("Missing \\qed")
            
            # Add extra \qed issues
            issues.extend(problem['extra_qed_issues'])
            
            if issues:
                file_issues.append({
                    'file': problem['file'],
                    'problem': problem['title'],
                    'issues': issues
                })
        
        return file_issues
    
    def check_all_files(self) -> None:
        """Check all chapter files and report issues."""
        chapter_files = self.find_chapter_files()
        
        if not chapter_files:
            print(f"No ch*.tex files found in {self.directory}")
            return
        
        if self.auto_fix:
            print(f"Auto-fixing issues in {len(chapter_files)} chapter files in {self.directory}...")
            print("=" * 60)
            
            total_missing_fixes = 0
            total_extra_fixes = 0
            total_importance_fixes = 0
            files_fixed = 0
            
            for file_path in chapter_files:
                missing_fixes = self.fix_missing_qed(file_path)
                extra_fixes = self.fix_extra_qed(file_path)
                importance_fixes = self.fix_importance_sections(file_path)
                
                if missing_fixes > 0 or extra_fixes > 0 or importance_fixes > 0:
                    files_fixed += 1
                    total_missing_fixes += missing_fixes
                    total_extra_fixes += extra_fixes
                    total_importance_fixes += importance_fixes
            
            print("\n" + "=" * 60)
            print("AUTO-FIX SUMMARY")
            print("=" * 60)
            print(f"Files processed: {len(chapter_files)}")
            print(f"Files fixed: {files_fixed}")
            print(f"Missing \\qed added: {total_missing_fixes}")
            print(f"Extra \\qed removed: {total_extra_fixes}")
            print(f"Importance sections wrapped: {total_importance_fixes}")
            print(f"Total fixes: {total_missing_fixes + total_extra_fixes + total_importance_fixes}")
            
            if total_missing_fixes + total_extra_fixes + total_importance_fixes == 0:
                print("✅ No issues found!")
            else:
                print(f"✅ Successfully applied {total_missing_fixes + total_extra_fixes + total_importance_fixes} fixes")
        else:
            print(f"Checking {len(chapter_files)} chapter files in {self.directory}...")
            print("=" * 60)
            
            total_issues = 0
            files_with_issues = 0
            
            for file_path in chapter_files:
                file_issues = self.check_file(file_path)
                
                if file_issues:
                    files_with_issues += 1
                    print(f"\n📁 {file_path.name}")
                    print("-" * 40)
                    
                    for issue in file_issues:
                        total_issues += len(issue['issues'])
                        print(f"  ❌ Problem: {issue['problem']}")
                        for problem_issue in issue['issues']:
                            print(f"     • {problem_issue}")
            
            # Summary
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(f"Files checked: {len(chapter_files)}")
            print(f"Files with issues: {files_with_issues}")
            print(f"Total problems with issues: {total_issues}")
            
            if total_issues == 0:
                print("✅ All problems are complete!")
            else:
                print(f"❌ Found {total_issues} issues across {files_with_issues} files")
    
    def generate_detailed_report(self) -> None:
        """Generate a detailed report of all problems and their status."""
        chapter_files = self.find_chapter_files()
        
        if not chapter_files:
            print(f"No ch*.tex files found in {self.directory}")
            return
        
        print(f"\nDETAILED REPORT - All Problems in {self.directory}")
        print("=" * 80)
        
        total_problems = 0
        complete_problems = 0
        
        for file_path in chapter_files:
            problems = self.extract_problems(file_path)
            if not problems:
                continue
                
            print(f"\n📁 {file_path.name} ({len(problems)} problems)")
            print("-" * 50)
            
            for problem in problems:
                total_problems += 1
                status_icons = []
                
                if problem['has_strategy']:
                    status_icons.append("✅ Strategy")
                else:
                    status_icons.append("❌ Strategy")
                
                if problem['has_solution']:
                    status_icons.append("✅ Solution")
                else:
                    status_icons.append("❌ Solution")
                
                # Check \qed status
                if problem['extra_qed_issues']:
                    if "Multiple \\qed" in str(problem['extra_qed_issues']):
                        status_icons.append("⚠️ Multiple \\qed")
                    elif "\\qed without Solution" in str(problem['extra_qed_issues']):
                        status_icons.append("⚠️ \\qed without Solution")
                    elif "Missing \\qed" in str(problem['extra_qed_issues']):
                        status_icons.append("❌ \\qed")
                elif problem['has_solution'] and problem['has_qed']:
                    status_icons.append("✅ \\qed")
                elif problem['has_solution']:
                    status_icons.append("❌ \\qed")
                
                # Determine if problem is complete
                has_extra_qed_issues = len(problem['extra_qed_issues']) > 0
                is_qed_correct = (problem['has_solution'] and problem['has_qed'] and not has_extra_qed_issues) or (not problem['has_solution'])
                
                if all([problem['has_strategy'], problem['has_solution'], is_qed_correct]):
                    complete_problems += 1
                    status = "✅ COMPLETE"
                else:
                    status = "❌ INCOMPLETE"
                
                print(f"  {status} {problem['title']}")
                print(f"    {' | '.join(status_icons)}")
                
                # Show extra \qed issues if any
                if problem['extra_qed_issues']:
                    for issue in problem['extra_qed_issues']:
                        print(f"    ⚠️ {issue}")
        
        print(f"\n" + "=" * 80)
        print(f"TOTAL: {complete_problems}/{total_problems} problems complete ({complete_problems/total_problems*100:.1f}%)")

def main():
    # Parse command line arguments
    args = sys.argv[1:]
    auto_fix = False
    detailed_report = False
    directory = "apostol"
    
    for arg in args:
        if arg == "--fix":
            auto_fix = True
        elif arg == "--detailed":
            detailed_report = True
        elif not arg.startswith("--"):
            directory = arg
    
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist")
        sys.exit(1)
    
    checker = ProblemChecker(directory, auto_fix)
    
    # Run the main check or auto-fix
    checker.check_all_files()
    
    # Show detailed report if requested
    if detailed_report and not auto_fix:
        checker.generate_detailed_report()

if __name__ == "__main__":
    main()
